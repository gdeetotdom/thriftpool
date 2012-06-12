from cpython cimport bool
from zmq.core.message cimport Frame
from socket_zmq.connection cimport Connection


cdef extern from "Python.h":
    ctypedef int Py_ssize_t
    object PyByteArray_FromStringAndSize(char *v, Py_ssize_t len)
    object PyMemoryView_FromObject(object)


cdef enum States:
    WAIT_LEN = 0
    WAIT_MESSAGE = 1
    WAIT_PROCESS = 2
    SEND_ANSWER = 3
    CLOSED = 4


cdef class SocketSource:

    cdef States status

    cdef int len
    cdef int recv_bytes
    cdef int sent_bytes

    cdef object socket
    cdef Connection connection
    cdef object io

    cdef object write_view
    cdef object read_view
    cdef object first_read_view

    cdef object read_watcher
    cdef object write_watcher

    cdef inline object allocate_buffer(self, Py_ssize_t size)

    cdef inline void setup_events(self) except *
    cdef inline void start_listen_read(self)
    cdef inline void stop_listen_read(self)
    cdef inline void start_listen_write(self)
    cdef inline void stop_listen_write(self)

    cdef inline bint is_writeable(self)
    cdef inline bint is_readable(self)
    cdef inline bint is_closed(self)
    cdef inline bint is_ready(self)

    cdef inline int read_length(self) except -1
    cdef inline void read(self) except *
    cdef inline void write(self) except *
    cdef close(self)

    cdef void ready(self, bool all_ok, object message) except *
    cpdef on_readable(self)
    cpdef on_writable(self)
