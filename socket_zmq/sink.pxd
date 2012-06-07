from zmq.core.socket cimport Socket as ZMQSocket
from zmq.core.message cimport Frame
from cpython cimport bool


cdef enum States:
    WAIT_MESSAGE = 1
    SEND_REQUEST = 2
    READ_REPLY = 3
    CLOSED = 4


cdef class ZMQSink:

    cdef ZMQSocket socket
    cdef object callback
    cdef bytes request
    cdef States status

    cdef object __read_watcher
    cdef object __write_watcher

    cdef __setup_events(self)
    
    cdef inline void start_listen_read(self)
    cdef inline void stop_listen_read(self)
    cdef inline void start_listen_write(self)
    cdef inline void stop_listen_write(self)

    cdef inline bint is_writeable(self)
    cdef inline bint is_readable(self)
    cdef inline bint is_ready(self)

    cdef read(self)
    cdef write(self)
    cdef close(self)

    cpdef ready(self, bytes request)
    cpdef on_readable(self)
    cpdef on_writable(self)
