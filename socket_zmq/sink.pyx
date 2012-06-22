# cython: profile=True
cimport cython
from cpython cimport bool
from zmq.core.constants import NOBLOCK, EAGAIN, FD, EVENTS, POLLIN, POLLOUT
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
        self.fileno = self.socket.getsockopt(FD)
        self.watcher = pyev.Io(self.fileno, pyev.EV_READ, loop, self.on_io)
        self.watcher.start()

    cdef bound(self, Connection connection):
        self.connection = connection

    cdef unbound(self):
        self.connection = None

    cdef inline void reset(self, events):
        self.watcher.stop()
        self.watcher.set(self.fileno, events)
        self.watcher.start()

    cdef inline void start_listen_write(self):
        self.reset(pyev.EV_READ | pyev.EV_WRITE)

    cdef inline void stop_listen_write(self):
        self.reset(pyev.EV_READ)

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
        self.request = None
        self.status = READ_REPLY

    @cython.locals(ready=cython.bint)
    cpdef close(self):
        assert not self.is_closed(), 'sink already closed'
        self.status = CLOSED
        self.socket.close()
        self.watcher.stop()
        self.watcher = None

    cdef inline ready(self, object request):
        assert self.is_ready(), 'sink not ready'
        self.status = SEND_REQUEST
        self.request = request
        self.start_listen_write()

    cpdef on_io(self, object watcher, object revents):
        try:
            events = self.socket.getsockopt(EVENTS)
            if events & POLLIN:
                self.on_readable()
            elif events & POLLOUT:
                self.on_writable()
        except ZMQError, e:
            if e.errno == EAGAIN:
                return
            self.close()
            raise
        except:
            self.close()
            raise

    cdef on_readable(self):
        while self.is_readable():
            self.read()

    cdef on_writable(self):
        while self.is_writeable():
            self.write()
        self.stop_listen_write()
        self.on_readable()
