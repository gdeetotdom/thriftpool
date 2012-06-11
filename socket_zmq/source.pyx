# cython: profile=True
cimport cython
from cpython cimport bool
from cpython.bytes cimport PyBytes_Format, PyBytes_AsString
from gevent.core import MAXPRI, MINPRI
from gevent.socket import EAGAIN, error
from struct import unpack_from, pack, calcsize
from zmq.core.message cimport Frame
from socket_zmq.connection cimport Connection


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

    def __init__(self, object io, object socket, Connection connection):
        self.io = io
        self.socket = socket
        self.static_read_view = PyMemoryView_FromObject(
                            PyByteArray_FromStringAndSize(NULL, BUFFER_SIZE))
        self.read_view = None
        self.write_view = None
        self.connection = connection
        self.setup_events()
        self.start_listen_read()

    @cython.locals(fileno=cython.int)
    cdef inline void setup_events(self):
        io = self.io
        fileno = self.socket.fileno()

        self.read_watcher = io(fileno, 1, priority=MINPRI)
        self.write_watcher = io(fileno, 2, priority=MAXPRI)

    @cython.profile(False)
    cdef inline void start_listen_read(self):
        """Start listen read events."""
        self.read_watcher.start(self.on_readable)

    @cython.profile(False)
    cdef inline void stop_listen_read(self):
        """Stop listen read events."""
        self.read_watcher.stop()

    @cython.profile(False)
    cdef inline void start_listen_write(self):
        """Start listen write events."""
        self.write_watcher.start(self.on_writable)

    @cython.profile(False)
    cdef inline void stop_listen_write(self):
        self.write_watcher.stop()

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
    cdef inline int read_length(self) except *:
        """Reads length of request."""
        static_read_view = self.static_read_view
        received = self.socket.recv_into(static_read_view, BUFFER_SIZE)

        if received == 0:
            # if we read 0 bytes and message is empty, it means client
            # close connection
            self.close()
            return 0

        assert received >= LENGTH_SIZE, "message length can't be read"

        message_length = unpack_from(LENGTH_FORMAT,
                            static_read_view[0:LENGTH_SIZE].tobytes())[0]
        assert message_length > 0, "negative or empty frame size, it seems" \
                                   " client doesn't use FramedTransport"
        self.len = message_length

        read_view = PyMemoryView_FromObject(
                        PyByteArray_FromStringAndSize(NULL, message_length))
        read_view[0:] = static_read_view[LENGTH_SIZE:received]
        self.read_view = read_view

        self.status = WAIT_MESSAGE

        return received - LENGTH_SIZE

    @cython.locals(readed=cython.int)
    cdef inline void read(self) except *:
        """Reads data from stream and switch state."""
        assert self.is_readable()

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
    cdef inline void write(self) except *:
        """Writes data from socket and switch state."""
        assert self.is_writeable()

        sent = self.socket.send(self.write_view[self.sent_bytes:])
        self.sent_bytes += sent

        if self.sent_bytes == self.len:
            self.status = WAIT_LEN
            self.write_view = None
            self.len = 0
            self.sent_bytes = 0

    cdef close(self):
        """Closes connection."""
        assert not self.is_closed()
        self.status = CLOSED
        self.stop_listen_read()
        self.stop_listen_write()
        self.socket.close()
        self.connection.close()
        self.connection = None

    @cython.locals(message_length=cython.int)
    cdef void ready(self, bool all_ok, object message) except *:
        """The ready can switch Connection to three states:

            WAIT_LEN if request was oneway.
            SEND_ANSWER if request was processed in normal way.
            CLOSED if request throws unexpected exception.

        """
        assert self.is_ready()

        if not all_ok:
            self.close()
            return

        message_length = len(message)
        if message_length == 0:
            # it was a oneway request, do not write answer
            self.message = None
            self.status = WAIT_LEN
        else:
            self.write_view = \
                PyMemoryView_FromObject(
                    PyByteArray_FromStringAndSize(NULL,
                        message_length + LENGTH_SIZE))
            self.write_view[0:LENGTH_SIZE] = pack(LENGTH_FORMAT,
                                                  message_length)
            self.write_view[LENGTH_SIZE:] = message
            message_length += LENGTH_SIZE
            self.status = SEND_ANSWER
            self.start_listen_write()

        self.len = message_length

    cpdef on_readable(self):
        assert self.is_readable()
        try:
            while self.is_readable():
                self.read()
            if self.is_ready():
                self.connection.on_request(self.read_view)
        except error, e:
            if e.errno != EAGAIN:
                self.close()
                raise
        except:
            self.close()
            raise

    cpdef on_writable(self):
        assert self.is_writeable()
        try:
            while self.is_writeable():
                self.write()
            if self.is_readable():
                self.stop_listen_write()
        except error, e:
            if e.errno != EAGAIN:
                self.close()
                raise
        except:
            self.close()
            raise
