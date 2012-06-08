from cpython cimport bool
from zmq.core.message cimport Frame


cdef extern from "Python.h":
    ctypedef int Py_ssize_t
    ctypedef struct PyMemoryViewObject:
        pass
    ctypedef struct Py_buffer:
        void *buf
        Py_ssize_t len
        int readonly
        char *format
        int ndim
        Py_ssize_t *shape
        Py_ssize_t *strides
        Py_ssize_t *suboffsets
        Py_ssize_t itemsize
        void *internal

    object PyByteArray_FromStringAndSize(char *v, Py_ssize_t len)
    object PyMemoryView_FromObject(object)
    Py_buffer *PyMemoryView_GET_BUFFER(object obj)


cdef enum States:
    WAIT_LEN = 0
    WAIT_MESSAGE = 1
    WAIT_PROCESS = 2
    SEND_ANSWER = 3
    CLOSED = 4


cdef class SocketSource:

    cdef int len
    cdef int fileno
    cdef States status

    cdef int recv_bytes
    cdef int sent_bytes

    cdef object socket
    cdef object callback
    cdef object format

    cdef object message
    cdef object read_view
    cdef object static_read_view

    cdef object read_watcher
    cdef object write_watcher

    cdef setup_events(self)

    cdef inline void start_listen_read(self)
    cdef inline void stop_listen_read(self)
    cdef inline void start_listen_write(self)
    cdef inline void stop_listen_write(self)

    cdef inline bint is_writeable(self)
    cdef inline bint is_readable(self)
    cdef inline bint is_closed(self)
    cdef inline bint is_ready(self)

    cdef read_length(self)
    cdef read(self)
    cdef write(self)
    cdef close(self)

    cpdef ready(self, bool all_ok, bytes message)
    cpdef on_readable(self)
    cpdef on_writable(self)
