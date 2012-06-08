# cython: profile=True
cimport cython
from cpython cimport bool
from cpython.bytes cimport PyBytes_Format, PyBytes_AsString
from gevent.core import MAXPRI
from gevent.hub import get_hub
from gevent.socket import EAGAIN, error
import struct
from zmq.core.message cimport Frame


LENGTH_SIZE = 4


cdef inline unsigned int pack(unsigned int i):
    cdef unsigned int j
    cdef unsigned int ret = 0
    for j from 0 <= j < LENGTH_SIZE:
        (<unsigned char *>&ret)[j] = (<unsigned char *>&i)[LENGTH_SIZE - j - 1]
    return ret


cdef inline unsigned int unpack(char * c):
    cdef unsigned int j
    cdef unsigned int ret = 0
    for j from 0 <= j < LENGTH_SIZE:
        (<unsigned char *>&ret)[j] = c[LENGTH_SIZE - j - 1]
    return ret


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

    def __init__(self, object socket, object callback):
        assert callable(callback)
        self.static_read_view = PyMemoryView_FromObject(
                                    PyByteArray_FromStringAndSize(NULL, 8192))
        self.read_view = None
        self.message = None
        self.format = struct.Struct('!i')
        self.socket = socket._sock
        self.fileno = self.socket.fileno()
        self.callback = callback
        self.setup_events()
        self.start_listen_read()

    cdef setup_events(self):
        loop = get_hub().loop
        io = loop.io

        self.read_watcher = io(self.fileno, 1, priority=MAXPRI)
        self.write_watcher = io(self.fileno, 2, priority=MAXPRI)

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

    @cython.locals(received=cython.int)
    cdef read_length(self):
        """Reads length of request."""
        received = self.socket.recv_into(self.static_read_view)

        if received == 0:
            # if we read 0 bytes and self.message is empty, it means client
            # close connection
            self.close()
            return 0

        assert received >= LENGTH_SIZE, "message length can't be read"

        cdef Py_buffer * buf = PyMemoryView_GET_BUFFER(
                                        self.static_read_view[:LENGTH_SIZE])
        self.len = unpack(<char *>buf.buf)

        assert self.len > 0, "negative or empty frame size, it seems client" \
            " doesn't use FramedTransport"

        self.read_view = PyMemoryView_FromObject(
                        PyByteArray_FromStringAndSize(NULL, self.len))
        self.read_view[0:] = self.static_read_view[LENGTH_SIZE:received]

        self.status = WAIT_MESSAGE

        return received - LENGTH_SIZE

    @cython.locals(readed=cython.int)
    cdef read(self):
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
    cdef write(self):
        """Writes data from socket and switch state."""
        assert self.is_writeable()

        sent = self.socket.send(self.message[self.sent_bytes:])
        self.sent_bytes += sent

        if self.sent_bytes == self.len:
            self.status = WAIT_LEN
            self.message = None
            self.len = 0
            self.sent_bytes = 0

    cdef close(self):
        """Closes connection."""
        self.status = CLOSED
        self.stop_listen_read()
        self.stop_listen_write()
        self.socket.close()

    cpdef ready(self, bool all_ok, bytes message):
        """The ready can switch Connection to three states:

            WAIT_LEN if request was oneway.
            SEND_ANSWER if request was processed in normal way.
            CLOSED if request throws unexpected exception.

        """
        assert self.is_ready()

        if not all_ok:
            self.close()
            return

        self.len = len(message)
        self.recv_bytes = 0
        self.sent_bytes = 0
        if self.len == 0:
            # it was a oneway request, do not write answer
            self.message = None
            self.status = WAIT_LEN
        else:
            self.message = PyMemoryView_FromObject(
                PyByteArray_FromStringAndSize(NULL, self.len + LENGTH_SIZE))
            self.message[:LENGTH_SIZE] = self.format.pack(self.len)
            self.message[LENGTH_SIZE:] = message
            self.len = len(self.message)
            self.status = SEND_ANSWER
            self.start_listen_write()

    cpdef on_readable(self):
        assert self.is_readable()
        try:
            while self.is_readable():
                self.read()
            if self.is_ready():
                self.callback(self.read_view.tobytes())
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
