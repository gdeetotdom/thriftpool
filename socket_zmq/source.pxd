from socket_zmq.base cimport BaseSocket
from socket_zmq.pool cimport SinkPool
from socket_zmq.sink cimport ZMQSink


cdef extern from "Python.h":
    ctypedef int Py_ssize_t


cdef enum States:
    WAIT_LEN = 0
    WAIT_MESSAGE = 1
    WAIT_PROCESS = 2
    SEND_ANSWER = 3
    CLOSED = 4


cdef class Buffer:

    cdef void *handle
    cdef int length
    cdef object view

    cdef resize(self, int size)
    cdef slice(self, int offset, int size=*)


cdef class SocketSource(BaseSocket):

    cdef object struct

    cdef States status
    cdef Py_ssize_t len
    cdef Py_ssize_t recv_bytes
    cdef Py_ssize_t sent_bytes

    cdef SinkPool pool
    cdef ZMQSink sink
    cdef object on_close
    cdef object socket
    cdef object address

    cdef Buffer buffer

    cdef inline bint is_writeable(self)
    cdef inline bint is_readable(self)
    cdef inline bint is_closed(self)
    cdef inline bint is_ready(self)

    cdef inline read_length(self)
    cdef inline read(self)
    cdef inline write(self)

    cpdef close(self)
    cpdef ready(self, object all_ok, object message)

    cpdef cb_io(self, object watcher, object revents)
    cdef on_readable(self)
    cdef on_writable(self)
