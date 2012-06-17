# cython: profile=True
cimport cython
from cpython cimport bool
from gevent.core import MAXPRI, MINPRI
from zmq.core.constants import FD
from zmq.core.error import ZMQError
from socket_zmq.connection cimport Connection
from zmq.core.libzmq cimport *
import pyev


cdef int NOBLOCK
cdef int EAGAIN = ZMQ_EAGAIN
if ZMQ_VERSION < 30000:
    # backport DONTWAIT as alias to NOBLOCK
    NOBLOCK = ZMQ_NOBLOCK
else:
    # keep NOBLOCK as alias for new DONTWAIT
    NOBLOCK = ZMQ_DONTWAIT


cdef class ZMQSink(object):

    def __init__(self, object loop, object socket):
        self.socket = socket
        self.on_response = None
        self.request = None
        self.status = WAIT_MESSAGE
        self.read_watcher = pyev.Io(self.socket.getsockopt(FD), pyev.EV_READ,
                                    loop, self.on_readable,
                                    priority=pyev.EV_MAXPRI)
        self.write_watcher = pyev.Io(self.socket.getsockopt(FD), pyev.EV_WRITE,
                                     loop, self.on_writable,
                                     priority=pyev.EV_MAXPRI)
        self.start_listen_read()

    cdef inline void start_listen_read(self):
        """Start listen read events."""
        self.read_watcher.start()

    cdef inline void stop_listen_read(self):
        """Stop listen read events."""
        self.read_watcher.stop()

    cdef inline void start_listen_write(self):
        """Start listen write events."""
        self.write_watcher.start()

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
        assert self.is_readable() and self.on_response is not None
        response = self.socket.recv(NOBLOCK)
        self.on_response(response)
        self.status = WAIT_MESSAGE

    cdef inline void write(self) except *:
        assert self.is_writeable()
        self.socket.send(self.request, NOBLOCK)
        self.status = READ_REPLY

    @cython.locals(ready=cython.bint)
    cdef close(self):
        assert not self.is_closed()
        self.status == CLOSED
        self.stop_listen_read()
        self.read_watcher = None
        self.stop_listen_write()
        self.write_watcher = None
        self.socket.close()
        self.connection = None

    cdef inline void ready(self, object request) except *:
        assert self.is_ready()
        self.status = SEND_REQUEST
        self.request = request
        self.start_listen_write()

    cpdef on_readable(self, object watcher, object revents):
        try:
            while self.is_readable():
                self.read()
        except ZMQError, e:
            if <int>e.errno != EAGAIN:
                self.close()
        except:
            self.close()
            raise

    cpdef on_writable(self, object watcher, object revents):
        try:
            while self.is_writeable():
                self.write()
        except ZMQError, e:
            if <int>e.errno != EAGAIN:
                self.close()
        except:
            self.close()
            raise
        else:
            self.stop_listen_write()
            self.on_readable(watcher, revents)
