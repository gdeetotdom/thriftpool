from cpython cimport bool


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
    cdef object recv_buffer

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

    cdef inline bytes content(self)
    cdef inline reset_recv_buffer(self, size)

    cdef inline read_length(self)
    cdef read(self)
    cdef write(self)
    cdef close(self)

    cpdef object ready(self, bool all_ok, object message)
    cpdef on_readable(self)
    cpdef on_writable(self)
