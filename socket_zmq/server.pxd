from zmq.core.socket cimport Socket


cdef class SocketPool(object):

    cdef object pool
    cdef object context
    cdef object frontend

    cdef inline Socket create(self)
    cdef inline Socket get(self)
    cdef inline void put(self, Socket sock) except *


cdef class StreamServer:

    cdef SocketPool pool

    cdef object loop
    cdef object socket
    cdef object watcher

    cpdef on_connection(self, object watcher, object revents)
    cpdef on_close(self, Socket socket)

    cdef inline handle(self, object socket)

    cpdef start(self)
    cpdef stop(self)
