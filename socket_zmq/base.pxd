
cdef class BaseSocket:

    cdef object fileno
    cdef object watcher

    cdef inline void reset(self, events)
    cdef inline void wait_writable(self)
    cdef inline void wait_readable(self)

    cpdef cb_io(self, object watcher, object revents)

    cpdef close(self)
