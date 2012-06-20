from socket_zmq.sink cimport ZMQSink
from zmq.core.context cimport Context
from socket_zmq.device cimport Device


cdef class SinkPool(object):

    cdef object loop
    cdef object pool
    cdef Context context
    cdef object frontend

    cdef inline ZMQSink create(self)

    cdef inline ZMQSink get(self)
    cdef inline void put(self, ZMQSink sock) except *


cdef class StreamServer:

    cdef SinkPool pool
    cdef Context context
    cdef Device device
    cdef object loop
    cdef object socket
    cdef object watcher

    cpdef on_connection(self, object watcher, object revents)
    cpdef on_close(self, ZMQSink sink)

    cdef inline handle(self, object socket)

    cpdef start(self)
    cpdef stop(self)
