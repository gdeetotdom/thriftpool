# cython: profile=True
from zmq.core.socket cimport Socket
from socket_zmq.base cimport BaseSocket


cdef enum States:
    WAIT_MESSAGE = 1
    SEND_REQUEST = 2
    READ_STATUS = 3
    READ_REPLY = 4
    CLOSED = 5


cdef class ZMQSink(BaseSocket):

    cdef object callback
    cdef Socket socket
    cdef object struct
    cdef object all_ok
    cdef object request
    cdef object response
    cdef States status

    cdef inline bint is_writeable(self)
    cdef inline bint is_readable(self)
    cdef inline bint is_ready(self)
    cdef inline bint is_closed(self)

    cdef inline read_status(self)
    cdef inline read(self)
    cdef inline write(self)

    cpdef close(self)
    cpdef ready(self, object callback, object request)

    cpdef cb_io(self, object watcher, object revents)
    cdef on_readable(self)
    cdef on_writable(self)
