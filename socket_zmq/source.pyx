# cython: profile=True
cimport cython
import errno
from cpython cimport bool
from cpython.bytes cimport PyBytes_Format, PyBytes_AsString
import _socket
from struct import unpack_from, pack, calcsize
from zmq.core.message cimport Frame
from socket_zmq.connection cimport Connection
import pyev

NONBLOCKING = (errno.EAGAIN, errno.EWOULDBLOCK)

cdef object LENGTH_FORMAT = '!i'
cdef int LENGTH_SIZE = calcsize(LENGTH_FORMAT)
cdef int BUFFER_SIZE = 4096


cdef class SocketSource(object):
    """Basic class is represented connection.

    It can be in state:
        WAIT_LEN --- connection is reading request len.
        WAIT_MESSAGE --- connection is reading request.
        WAIT_PROCESS --- connection has just read whole request and
            waits for call ready routine.
        SEND_ANSWER --- connection is sending answer string (including length
            of answer).
        CLOSED --- socket was closed and connection should be deleted.

    """

    def __cinit__(self):
        self.len = 0
        self.recv_bytes = 0
        self.sent_bytes = 0
        self.status = WAIT_LEN

    def __init__(self, object loop, object socket):
        self.socket = socket
        self.first_read_view = self.allocate_buffer(BUFFER_SIZE)
        self.read_view = None
        self.write_view = None
        self.connection = None
        self.watcher = pyev.Io(self.socket, pyev.EV_READ, loop, self.on_io)
        self.watcher.start()

    cdef inline object allocate_buffer(self, Py_ssize_t size):
        buf = PyMemoryView_FromObject(
                            PyByteArray_FromStringAndSize(NULL, size))
        return buf

    cdef bound(self, Connection connection):
        self.connection = connection

    cdef unbound(self):
        self.connection = None

    cdef inline void reset(self, events):
        self.watcher.stop()
        self.watcher.set(self.socket, events)
        self.watcher.start()

    cdef inline void start_listen_write(self):
        self.reset(pyev.EV_READ | pyev.EV_WRITE)

    cdef inline void stop_listen_write(self):
        self.reset(pyev.EV_READ)

    @cython.profile(False)
    cdef inline bint is_writeable(self):
        return self.status == SEND_ANSWER

    @cython.profile(False)
    cdef inline bint is_readable(self):
        return self.status == WAIT_LEN or self.status == WAIT_MESSAGE

    @cython.profile(False)
    cdef inline bint is_closed(self):
        "Returns True if connection is closed."
        return self.status == CLOSED

    @cython.profile(False)
    cdef inline bint is_ready(self):
        "Returns True if connection is ready."
        return self.status == WAIT_PROCESS

    @cython.locals(received=cython.int, message_length=cython.int)
    cdef inline read_length(self):
        """Reads length of request."""
        first_read_view = self.first_read_view
        received = self.socket.recv_into(first_read_view, BUFFER_SIZE)

        if received == 0:
            # if we read 0 bytes and message is empty, it means client
            # close connection
            self.close()
            return 0

        assert received >= LENGTH_SIZE, "message length can't be read"

        message_length = unpack_from(LENGTH_FORMAT,
                            first_read_view[0:LENGTH_SIZE].tobytes())[0]
        assert message_length > 0, "negative or empty frame size, it seems" \
                                   " client doesn't use FramedTransport"
        self.len = message_length + LENGTH_SIZE

        if self.len == received:
            self.read_view = first_read_view
        else:
            read_view = self.allocate_buffer(self.len)
            read_view[0:] = first_read_view[:received]
            self.read_view = read_view

        self.status = WAIT_MESSAGE

        return received

    @cython.locals(readed=cython.int)
    cdef inline read(self):
        """Reads data from stream and switch state."""
        assert self.is_readable(), 'socket in non-readable state'

        readed = 0

        if self.status == WAIT_LEN:
            readed = self.read_length()
            if self.is_closed():
                return

        elif self.status == WAIT_MESSAGE:
            readed = self.socket.recv_into(self.read_view[self.recv_bytes:],
                                           self.len - self.recv_bytes)

        assert readed > 0, "can't read frame from socket"

        self.recv_bytes += readed
        if self.recv_bytes == self.len:
            self.recv_bytes = 0
            self.status = WAIT_PROCESS

    @cython.locals(sent=cython.int)
    cdef inline write(self):
        """Writes data from socket and switch state."""
        assert self.is_writeable(), 'socket in non writable state'

        sent = self.socket.send(self.write_view[self.sent_bytes:])
        self.sent_bytes += sent

        if self.sent_bytes == self.len:
            self.status = WAIT_LEN
            self.write_view = None
            self.len = 0
            self.sent_bytes = 0

    cpdef close(self):
        """Closes connection."""
        assert not self.is_closed(), 'socket already closed'
        self.status = CLOSED
        self.socket.close()
        self.watcher.stop()
        self.watcher = None
        self.connection.close()

    @cython.locals(message_length=cython.int)
    cdef ready(self, bool all_ok, object message):
        """The ready can switch Connection to three states:

            WAIT_LEN if request was oneway.
            SEND_ANSWER if request was processed in normal way.
            CLOSED if request throws unexpected exception.

        """
        assert self.is_ready(), 'socket is not ready'

        if not all_ok:
            self.close()
            return

        message_length = len(message)
        if message_length == 0:
            # it was a oneway request, do not write answer
            self.message = None
            self.status = WAIT_LEN
        else:
            self.write_view = self.allocate_buffer(message_length + LENGTH_SIZE)
            self.write_view[0:LENGTH_SIZE] = pack(LENGTH_FORMAT, message_length)
            self.write_view[LENGTH_SIZE:] = message
            message_length += LENGTH_SIZE
            self.status = SEND_ANSWER
            self.start_listen_write()

        self.len = message_length

    cpdef on_io(self, object watcher, object revents):
        try:
            if revents & pyev.EV_READ:
                self.on_readable()
            else:
                self.on_writable()
        except _socket.error, e:
            if e.errno in NONBLOCKING:
                return
            self.close()
            raise
        except:
            self.close()
            raise

    cdef on_readable(self):
        while self.is_readable():
            self.read()
        if self.is_ready():
            self.connection.on_request(self.read_view[LENGTH_SIZE:])

    cdef on_writable(self):
        while self.is_writeable():
            self.write()
        if self.is_readable():
            self.stop_listen_write()
