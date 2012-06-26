# cython: profile=True
from zmq.core.socket cimport Socket
from socket_zmq.base cimport BaseSocket


cdef enum States:
    WAIT_MESSAGE = 1
    SEND_REQUEST = 2
    READ_REPLY = 3
    CLOSED = 4


cdef class ZMQSink(BaseSocket):

    cdef object callback
    cdef Socket socket
    cdef char[:] request
    cdef States status

    cdef inline bint is_writeable(self)
    cdef inline bint is_readable(self)
    cdef inline bint is_ready(self)
    cdef inline bint is_closed(self)

    cdef inline read(self)
    cdef inline write(self)

    cpdef close(self)
    cpdef ready(self, object callback, char[:] request)

    cpdef cb_io(self, object watcher, object revents)
    cdef on_readable(self)
    cdef on_writable(self)
