# cython: profile=True
cimport cython
from cpython cimport bool
from gevent.core import MAXPRI, MINPRI
from zmq.core.constants import FD
from zmq.core.error import ZMQError
from socket_zmq.connection cimport Connection
from zmq.core.libzmq cimport *


cdef int NOBLOCK
cdef int EAGAIN = ZMQ_EAGAIN
if ZMQ_VERSION < 30000:
    # backport DONTWAIT as alias to NOBLOCK
    NOBLOCK = ZMQ_NOBLOCK
else:
    # keep NOBLOCK as alias for new DONTWAIT
    NOBLOCK = ZMQ_DONTWAIT


cdef class ZMQSink(object):

    def __init__(self, object io, object socket, Connection connection):
        self.io = io
        self.socket = socket
        self.connection = connection
        self.request = None
        self.status = WAIT_MESSAGE
        self.setup_events()
        self.start_listen_read()

    @cython.locals(fileno=cython.int)
    cdef inline void setup_events(self) except *:
        io = self.io
        fileno = self.socket.getsockopt(FD)

        self.read_watcher = io(fileno, 1, priority=MAXPRI)
        self.write_watcher = io(fileno, 2, priority=MAXPRI)

    cdef inline void start_listen_read(self):
        """Start listen read events."""
        self.read_watcher.start(self.on_readable)

    cdef inline void stop_listen_read(self):
        """Stop listen read events."""
        self.read_watcher.stop()

    cdef inline void start_listen_write(self):
        """Start listen write events."""
        self.write_watcher.start(self.on_writable)

    cdef inline void stop_listen_write(self):
        """Stop listen write events."""
        self.write_watcher.stop()

    @cython.profile(False)
    cdef inline bint is_writeable(self):
        return self.status == SEND_REQUEST

    @cython.profile(False)
    cdef inline bint is_readable(self):
        return self.status == READ_REPLY

    @cython.profile(False)
    cdef inline bint is_ready(self):
        return self.status == WAIT_MESSAGE

    @cython.profile(False)
    cdef inline bint is_closed(self):
        return self.status == CLOSED

    cdef void read(self) except *:
        assert self.is_readable()
        response = self.socket.recv(NOBLOCK)
        self.connection.on_response(response)
        self.status = WAIT_MESSAGE

    cdef inline void write(self) except *:
        assert self.is_writeable()
        self.socket.send(self.request, NOBLOCK)
        self.status = READ_REPLY

    @cython.locals(ready=cython.bint)
    cdef close(self):
        assert not self.is_closed()
        ready = self.is_ready()
        self.status == CLOSED
        self.stop_listen_read()
        self.stop_listen_write()
        if not ready:
            self.socket.close()
        self.connection = None

    cdef inline void ready(self, object request) except *:
        assert self.is_ready()
        self.status = SEND_REQUEST
        self.request = request
        self.start_listen_write()

    cpdef on_readable(self):
        try:
            while self.is_readable():
                self.read()
        except ZMQError, e:
            if <int>e.errno != EAGAIN:
                self.close()
                raise
        except:
            self.close()
            raise

    cpdef on_writable(self):
        try:
            while self.is_writeable():
                self.write()
        except ZMQError, e:
            if <int>e.errno != EAGAIN:
                self.close()
                raise
        except:
            self.close()
            raise
        else:
            self.stop_listen_write()
            self.on_readable()
