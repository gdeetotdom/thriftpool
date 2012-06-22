# cython: profile=True
from zmq.core.socket cimport Socket
from socket_zmq.connection cimport Connection


cdef enum States:
    WAIT_MESSAGE = 1
    SEND_REQUEST = 2
    READ_REPLY = 3
    CLOSED = 4


cdef class ZMQSink:

    cdef Socket socket
    cdef Connection connection
    cdef object request
    cdef States status
    cdef object fileno
    cdef object watcher

    cdef bound(self, Connection connection)
    cdef unbound(self)

    cdef inline void reset(self, events)
    cdef inline void start_listen_write(self)
    cdef inline void stop_listen_write(self)

    cdef inline bint is_writeable(self)
    cdef inline bint is_readable(self)
    cdef inline bint is_ready(self)
    cdef inline bint is_closed(self)

    cdef inline read(self)
    cdef inline write(self)
    cdef inline ready(self, object request)
    cpdef close(self)

    cpdef on_io(self, object watcher, object revents)
    cdef on_readable(self)
    cdef on_writable(self)

