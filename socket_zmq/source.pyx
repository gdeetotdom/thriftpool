# cython: profile=True
cimport cython
from logging import getLogger
from pyev import EV_READ, EV_WRITE, EV_ERROR
from struct import unpack, pack, calcsize
import _socket
import errno
from cpython cimport bool
from socket_zmq.server cimport SinkPool
from socket_zmq.base cimport BaseSocket
from socket_zmq.sink cimport ZMQSink

logger = getLogger(__name__)

NONBLOCKING = (errno.EAGAIN, errno.EWOULDBLOCK)
LENGTH_FORMAT = '!i'
cdef int LENGTH_SIZE = calcsize(LENGTH_FORMAT)
cdef int BUFFER_SIZE = 4096


cdef inline object allocate_buffer(Py_ssize_t size):
    """Create new style python buffer of given size."""
    return PyMemoryView_FromObject(
                        PyByteArray_FromStringAndSize(NULL, size))


cdef class SocketSource(BaseSocket):
    """Basic class is represented connection.

    It can be in state:
        WAIT_LEN --- connection is reading request length.
        WAIT_MESSAGE --- connection is reading request.
        WAIT_PROCESS --- connection has just read whole request and
            waits for call ready routine.
        SEND_ANSWER --- connection is sending answer string (including length
            of answer).
        CLOSED --- socket was closed and connection should be deleted.

    """

    def __init__(self, SinkPool pool, object loop, object socket,
                 object on_close):
        self.write_view = self.read_view = None
        self.sent_bytes = self.recv_bytes = self.len = 0
        self.status = WAIT_LEN
        self.on_close = on_close
        self.socket = socket
        self.pool = pool
        self.sink = self.pool.get()
        self.first_read_view = allocate_buffer(BUFFER_SIZE)
        BaseSocket.__init__(self, loop, self.socket.fileno())

    @cython.profile(False)
    cdef inline bint is_writeable(self):
        """Returns ``True`` if source is writable."""
        return self.status == SEND_ANSWER

    @cython.profile(False)
    cdef inline bint is_readable(self):
        """Returns ``True`` if source is readable."""
        return self.status == WAIT_LEN or self.status == WAIT_MESSAGE

    @cython.profile(False)
    cdef inline bint is_closed(self):
        """Returns ``True`` if source is closed."""
        return self.status == CLOSED

    @cython.profile(False)
    cdef inline bint is_ready(self):
        """Returns ``True`` if source is ready."""
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

        message_length = unpack(LENGTH_FORMAT,
                            first_read_view[0:LENGTH_SIZE].tobytes())[0]
        assert message_length > 0, "negative or empty frame size, it seems" \
                                   " client doesn't use FramedTransport"
        self.len = message_length + LENGTH_SIZE

        if self.len == received:
            self.read_view = first_read_view
        else:
            read_view = allocate_buffer(self.len)
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

    cdef inline write(self):
        """Writes data from socket and switch state."""
        assert self.is_writeable(), 'socket in non writable state'

        self.sent_bytes += self.socket.send(self.write_view[self.sent_bytes:])

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
        if self.sink.is_ready():
            self.pool.put(self.sink)
        elif not self.sink.is_closed():
            self.sink.close()
        self.sink = None
        self.on_close(self)
        self.on_close = None
        BaseSocket.close(self)

    @cython.locals(message_length=cython.int)
    cpdef ready(self, bool all_ok, object message):
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
            self.write_view = allocate_buffer(message_length + LENGTH_SIZE)
            self.write_view[0:LENGTH_SIZE] = pack(LENGTH_FORMAT, message_length)
            self.write_view[LENGTH_SIZE:] = message
            message_length += LENGTH_SIZE
            self.status = SEND_ANSWER
            self.wait_writable()

        self.len = message_length

    cpdef cb_io(self, object watcher, object revents):
        if revents & EV_ERROR:
            self.close()
        try:
            if revents & EV_WRITE:
                self.on_writable()
            elif revents & EV_READ:
                self.on_readable()
        except _socket.error, e:
            if e.errno in NONBLOCKING:
                return
            self.close()
            logger.exception(e)
        except Exception, e:
            self.close()
            logger.exception(e)

    cdef on_readable(self):
        while self.is_readable():
            self.read()
        if self.is_ready():
            self.sink.ready(self.ready, self.read_view[LENGTH_SIZE:])

    cdef on_writable(self):
        while self.is_writeable():
            self.write()
        if self.is_readable():
            self.wait_readable()
