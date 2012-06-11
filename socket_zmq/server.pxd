from zmq.core.socket cimport Socket


cdef class StreamServer:

    cdef object io
    cdef object socket
    cdef object watcher
    cdef object context
    cdef object frontend
    cdef object stop_wait

    cdef inline Socket create_backend(self)

    cpdef on_connection(self)
    cpdef handle(self, object socket, object address)

    cpdef serve_forever(self)
    cpdef stop(self)
