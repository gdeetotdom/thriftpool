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

    cdef object write_view
    cdef object read_view
    cdef object first_read_view

    cdef object watcher

    cdef inline object allocate_buffer(self, Py_ssize_t size)

    cdef bound(self, Connection connection)
    cdef unbound(self)

    cdef inline void reset(self, events)
    cdef inline void start_listen_write(self)
    cdef inline void stop_listen_write(self)

    cdef inline bint is_writeable(self)
    cdef inline bint is_readable(self)
    cdef inline bint is_closed(self)
    cdef inline bint is_ready(self)

    cdef inline read_length(self)
    cdef inline read(self)
    cdef inline write(self)
    cdef ready(self, bool all_ok, object message)
    cpdef close(self)

    cpdef on_io(self, object watcher, object revents)
    cdef on_readable(self)
    cdef on_writable(self)
