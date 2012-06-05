# cython: profile=True
cimport cython
from cpython cimport bool
from gevent.core import MAXPRI
from gevent.hub import get_hub
from gevent.socket import EAGAIN, error
import struct


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
        """We need to allocate std::string. Us it as buffer."""
        self.len = 0
        self.recv_bytes = 0
        self.sent_bytes = 0
        self.status = WAIT_LEN

    def __init__(self, socket, callback):
        assert callable(callback)
        self.recv_buffer = None
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
        """Stop listen write events."""
        self.write_watcher.stop()

    @cython.profile(False)
    cdef inline bint is_writeable(self):
        "Returns True if connection should be added to write list of select."
        return self.status == SEND_ANSWER

    @cython.profile(False)
    cdef inline bint is_readable(self):
        "Returns True if connection should be added to read list of select."
        return self.status == WAIT_LEN or self.status == WAIT_MESSAGE

    @cython.profile(False)
    cdef inline bint is_closed(self):
        "Returns True if connection is closed."
        return self.status == CLOSED

    @cython.profile(False)
    cdef inline bint is_ready(self):
        "Returns True if connection is ready."
        return self.status == WAIT_PROCESS

    cdef inline bytes content(self):
        return self.recv_buffer.tobytes()

    cdef inline reset_recv_buffer(self, size):
        self.recv_buffer = memoryview(bytearray(size))

    @cython.locals(readed=cython.int)
    cdef inline read_length(self):
        """Reads length of request."""
        read = self.socket.recv(4)
        readed = len(read)

        if readed == 0:
            # if we read 0 bytes and self.message is empty, it means client
            # close connection
            self.close()
            return

        assert readed == 4, 'message length can\'t be read'

        self.len, = self.format.unpack(read)

        assert self.len >= 0, "negative frame size, it seems client" \
            " doesn't use FramedTransport"
        assert self.len != 0, "empty frame, it's really strange"

        self.reset_recv_buffer(self.len)
        self.status = WAIT_MESSAGE

    @cython.locals(readed=cython.int)
    cdef read(self):
        """Reads data from stream and switch state."""
        assert self.is_readable()

        if self.status == WAIT_LEN:
            self.read_length()

            # try to read rest part of buffer
            if self.status == WAIT_MESSAGE:
                self.read()

        elif self.status == WAIT_MESSAGE:
            readed = self.socket.recv_into(self.recv_buffer[self.recv_bytes:],
                                           self.len - self.recv_bytes)
            assert readed > 0, "can't read frame from socket "

            self.recv_bytes += readed
            if self.recv_bytes == self.len:
                self.recv_bytes = 0
                self.status = WAIT_PROCESS

    @cython.locals(sent=cython.int)
    cdef write(self):
        """Writes data from socket and switch state."""
        assert self.is_writeable() and self.message is not None

        sent = self.socket.send(buffer(self.message, self.sent_bytes))
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

    cpdef object ready(self, bool all_ok, object message):
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
            self.start_listen_read()
        else:
            self.message = '{0}{1}'.format(self.format.pack(self.len),
                                           message)
            self.len = len(self.message)
            self.status = SEND_ANSWER
            self.start_listen_write()

    cpdef on_readable(self):
        assert self.is_readable()
        try:
            while self.is_readable():
                self.read()
            if self.is_ready():
                self.stop_listen_read()
                self.callback(self.content())
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
                self.start_listen_read()
            elif self.is_closed():
                self.stop_listen_write()
        except error, e:
            if e.errno != EAGAIN:
                self.close()
                raise
        except:
            self.close()
            raise
