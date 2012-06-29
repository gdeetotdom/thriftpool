from socket_zmq.sink cimport ZMQSink
from zmq.core.context cimport Context


cdef class SinkPool(object):

    cdef int size
    cdef object loop
    cdef object pool
    cdef Context context
    cdef object frontend

    cdef inline ZMQSink create(self)
    cdef inline ZMQSink get(self)
    cdef inline put(self, ZMQSink sock)
    cpdef close(self)
