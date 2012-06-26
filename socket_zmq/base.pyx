"""Contains class:`BaseSocket`."""
from pyev import Io, EV_READ, EV_WRITE


cdef class BaseSocket:
    """Base class for sources and sinks."""

    def __init__(self, object loop, object fileno):
        self.fileno = fileno
        self.watcher = Io(self.fileno, EV_READ, loop, self.cb_io)
        self.watcher.start()

    cdef inline void reset(self, events):
        """Reset watcher state."""
        self.watcher.stop()
        self.watcher.set(self.fileno, events)
        self.watcher.start()

    cdef inline void wait_writable(self):
        """Wait for file descriptor has become readable and/or writable."""
        self.reset(EV_READ | EV_WRITE)

    cdef inline void wait_readable(self):
        """Wait for file descriptor has become readable."""
        self.reset(EV_READ)

    cpdef cb_io(self, object watcher, object revents):
        """Called when file descriptor become readable or writable."""
        raise NotImplementedError()

    cpdef close(self):
        """Closes and unset watcher."""
        self.watcher.stop()
        self.watcher = None
