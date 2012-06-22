# cython: profile=True
cimport cython
from cpython cimport bool
from zmq.core.constants import NOBLOCK, EAGAIN, FD
from zmq.core.error import ZMQError
import pyev
from socket_zmq.connection cimport Connection
from zmq.core.libzmq cimport *
from zmq.core.socket cimport Socket
from socket_zmq.connection cimport Connection


cdef class ZMQSink(object):

    def __init__(self, object loop, Socket socket):
        self.socket = socket
        self.connection = None
        self.request = None
        self.status = WAIT_MESSAGE
        self.read_watcher = pyev.Io(self.socket.getsockopt(FD), pyev.EV_READ,
                                    loop, self.on_readable,
                                    priority=pyev.EV_MAXPRI)
        self.write_watcher = pyev.Io(self.socket.getsockopt(FD), pyev.EV_WRITE,
                                     loop, self.on_writable,
                                     priority=pyev.EV_MAXPRI)
        self.start_listen_read()

    cdef bound(self, Connection connection):
        self.connection = connection

    cdef unbound(self):
        self.connection = None

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

    cdef inline read(self):
        assert self.is_readable(), 'sink not readable'
        response = self.socket.recv(NOBLOCK)
        self.connection.on_response(response)
        self.status = WAIT_MESSAGE

    cdef inline write(self):
        assert self.is_writeable(), 'sink not writable'
        self.socket.send(self.request, NOBLOCK)
        self.status = READ_REPLY

    @cython.locals(ready=cython.bint)
    cpdef close(self):
        assert not self.is_closed(), 'sink already closed'
        self.status = CLOSED
        self.stop_listen_read()
        self.stop_listen_write()
        self.socket.close()

    cdef inline ready(self, object request):
        assert self.is_ready(), 'sink not ready'
        self.status = SEND_REQUEST
        self.request = request
        self.start_listen_write()

    def on_readable(self, object watcher, object revents):
        try:
            while self.is_readable():
                self.read()
        except ZMQError, e:
            if e.errno == EAGAIN:
                return
            self.close()
            raise
        except:
            self.close()
            raise

    def on_writable(self, object watcher, object revents):
        try:
            while self.is_writeable():
                self.write()
        except ZMQError, e:
            if e.errno == EAGAIN:
                return
            self.close()
            raise
        except:
            self.close()
            raise
        else:
            self.stop_listen_write()
            self.on_readable(watcher, revents)
