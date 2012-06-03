from cpython cimport bool
from libcpp.string cimport string


cdef enum States:
    WAIT_LEN = 0
    WAIT_MESSAGE = 1
    WAIT_PROCESS = 2
    SEND_ANSWER = 3
    CLOSED = 4


cdef class SocketSource:

    cdef size_t len
    cdef int fileno
    cdef string *message
    cdef States status

    cdef object socket
    cdef object format
    cdef object callback

    cdef object __read_watcher
    cdef object __write_watcher

    cpdef __setup_events(self)

    cdef inline void start_listen_read(self)
    cdef inline void stop_listen_read(self)
    cdef inline void start_listen_write(self)
    cdef inline void stop_listen_write(self)

    cdef inline bool is_writeable(self)
    cdef inline bool is_readable(self)
    cdef inline bool is_closed(self)
    cdef inline bool is_ready(self)

    cdef inline bytes content(self)
    cdef inline void expunge(self, int sent)

    cdef inline _read_len(self)
    cdef read(self)
    cdef inline int _send(self)
    cdef write(self)
    cdef close(self)

    cpdef object ready(self, bool all_ok, object message)
    cpdef on_readable(self)
    cpdef on_writable(self)
