from socket_zmq.pool cimport SinkPool
from zmq.core.context cimport Context


cdef class Proxy:

    cdef object connections
    cdef SinkPool pool
    cdef Context context
    cdef object loop
    cdef object socket
    cdef object watcher
    cdef object backlog
