cimport cython
from pyev import EV_ERROR
from cpython cimport bool
from logging import getLogger
from zmq.core.constants import NOBLOCK, EAGAIN, FD, EVENTS, POLLIN, POLLOUT
from zmq.core.error import ZMQError
from zmq.core.socket cimport Socket
from socket_zmq.base cimport BaseSocket

logger = getLogger(__name__)


cdef class ZMQSink(BaseSocket):

    def __init__(self, object loop, Socket socket):
        self.request = self.callback = None
        self.socket = socket
        self.status = WAIT_MESSAGE
        BaseSocket.__init__(self, loop, self.socket.getsockopt(FD))

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
        assert self.callback is not None, 'callback is none'
        self.callback(True, self.socket.recv(NOBLOCK))
        self.callback = None
        self.status = WAIT_MESSAGE

    cdef inline write(self):
        assert self.is_writeable(), 'sink not writable'
        assert self.request is not None, 'request is none'
        self.socket.send(self.request, NOBLOCK)
        self.request = None
        self.status = READ_REPLY

    @cython.locals(ready=cython.bint)
    cpdef close(self):
        assert not self.is_closed(), 'sink already closed'
        self.status = CLOSED
        self.socket.close()
        BaseSocket.close(self)

    cpdef ready(self, object callback, char[:] request):
        assert self.is_ready(), 'sink not ready'
        self.callback = callback
        self.request = request
        self.status = SEND_REQUEST
        self.wait_writable()

    cpdef cb_io(self, object watcher, object revents):
        if revents & EV_ERROR:
            self.close()
            return
        try:
            events = self.socket.getsockopt(EVENTS)
            if events & POLLOUT:
                self.on_writable()
            if events & POLLIN:
                self.on_readable()
        except ZMQError, e:
            if e.errno == EAGAIN:
                return
            self.close()
            logger.exception(e)
        except:
            self.close()
            raise

    cdef on_readable(self):
        while self.is_readable():
            self.read()

    cdef on_writable(self):
        while self.is_writeable():
            self.write()
        if self.is_readable():
            self.wait_readable()
            self.on_readable()
