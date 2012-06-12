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
    cdef object io

    cdef object read_watcher
    cdef object write_watcher

    cdef inline void setup_events(self) except *
    cdef inline void start_listen_read(self)
    cdef inline void stop_listen_read(self)
    cdef inline void start_listen_write(self)
    cdef inline void stop_listen_write(self)

    cdef inline bint is_writeable(self)
    cdef inline bint is_readable(self)
    cdef inline bint is_ready(self)
    cdef inline bint is_closed(self)

    cdef inline void read(self) except *
    cdef inline void write(self) except *
    cdef close(self)

    cdef void ready(self, object request) except *
    cpdef on_readable(self)
    cpdef on_writable(self)
