cimport cython
from cpython cimport bool
from gevent.core import MAXPRI, MINPRI
from zmq import TYPE, REQ, NOBLOCK, EAGAIN, FD, ZMQError
from socket_zmq.connection cimport Connection


cdef class ZMQSink(object):

    def __init__(self, object loop, object socket, Connection connection):
        assert socket.getsockopt(TYPE) == REQ
        self.loop = loop
        self.socket = socket
        self.connection = connection
        self.request = None
        self.status = WAIT_MESSAGE
        self.setup_events()

    @cython.locals(fileno=cython.int)
    cdef inline void setup_events(self):
        io = self.loop.io
        fileno = self.socket.getsockopt(FD)

        self.read_watcher = io(fileno, 1, priority=MINPRI)
        self.write_watcher = io(fileno, 2, priority=MAXPRI)

    @cython.profile(False)
    cdef inline void start_listen_read(self):
        """Start listen read events."""
        self.read_watcher.start(self.on_readable)

    @cython.profile(False)
    cdef inline void stop_listen_read(self):
        """Stop listen read events."""
        self.read_watcher.stop()

    @cython.profile(False)
    cdef inline void start_listen_write(self):
        """Start listen write events."""
        self.write_watcher.start(self.on_writable)

    @cython.profile(False)
    cdef inline void stop_listen_write(self):
        """Stop listen write events."""
        self.write_watcher.stop()

    @cython.profile(False)
    cdef inline bint is_writeable(self):
        return self.status == SEND_REQUEST

    @cython.profile(False)
    cdef inline bint is_readable(self):
        return self.status == READ_REPLY

    @cython.profile(False)
    cdef inline bint is_ready(self):
        return self.status == WAIT_MESSAGE

    @cython.profile(False)
    cdef inline bint is_closed(self):
        return self.status == CLOSED

    @cython.locals(response=cython.bytes)
    cdef void read(self) except *:
        assert self.is_readable()
        response = self.socket.recv(NOBLOCK)
        self.connection.on_response(response)
        self.status = WAIT_MESSAGE

    cdef inline void write(self) except *:
        assert self.is_writeable()
        self.socket.send(self.request, NOBLOCK)
        self.status = READ_REPLY

    cdef close(self):
        assert not self.is_closed()
        self.status == CLOSED
        self.stop_listen_read()
        self.stop_listen_write()
        self.socket.close()

    cdef inline void ready(self, object request) except *:
        assert self.is_ready()
        self.status = SEND_REQUEST
        self.request = request
        self.start_listen_write()

    cpdef on_readable(self):
        try:
            while self.is_readable():
                self.read()
        except ZMQError, e:
            if e.errno != EAGAIN:
                self.close()
                raise
        except:
            self.close()
            raise
        else:
            self.stop_listen_read()

    cpdef on_writable(self):
        try:
            while self.is_writeable():
                self.write()
        except ZMQError, e:
            if e.errno != EAGAIN:
                self.close()
                raise
        except:
            self.close()
            raise
        else:
            self.stop_listen_write()
            self.on_readable()
            self.start_listen_read()
