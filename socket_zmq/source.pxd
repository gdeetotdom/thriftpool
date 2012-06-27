from socket_zmq.base cimport BaseSocket
from socket_zmq.server cimport SinkPool
from socket_zmq.sink cimport ZMQSink
from cpython cimport array


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


cdef class SocketSource(BaseSocket):

    cdef States status

    cdef int len
    cdef int recv_bytes
    cdef int sent_bytes

    cdef SinkPool pool
    cdef ZMQSink sink
    cdef object on_close
    cdef object socket

    cdef char[:] buffer

    cdef inline void resize(self, Py_ssize_t size)

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
