# cython: profile=True
import cython
from errno import EWOULDBLOCK
from socket_zmq.connection cimport Connection
from zmq.core.socket cimport Socket
from collections import deque
import zmq
import _socket
import pyev
import weakref


cdef class SocketPool(object):

    def __init__(self, object context, object frontend, object size=128):
        self.pool = deque(maxlen=size)
        self.context = context
        self.frontend = frontend

    @cython.locals(front_socket=Socket)
    cdef inline Socket create(self):
        front_socket = self.context.socket(zmq.REQ)
        front_socket.connect(self.frontend)
        return front_socket

    @cython.locals(sock=Socket)
    cdef inline Socket get(self):
        try:
            sock = self.pool.popleft()
        except IndexError:
            sock = self.create()
        return sock

    cdef inline void put(self, Socket sock) except *:
        self.pool.append(sock)


cdef class StreamServer(object):

    def __init__(self, object context, object frontend, object socket):
        self.loop = pyev.Loop()
        self.pool = SocketPool(context, frontend)
        self.socket = socket._sock
        self.watcher = pyev.Io(self.socket, pyev.EV_READ,
                               self.loop, self.on_connection,
                               priority=pyev.EV_MINPRI)
        self.watcher.start()

    cpdef on_connection(self, object watcher, object revents):
        try:
            result = self.socket.accept()
        except _socket.error, err:
            if err[0] == EWOULDBLOCK:
                return
            raise
        client_socket = result[0]
        client_socket.setblocking(0)
        client_socket.setsockopt(_socket.SOL_TCP, _socket.TCP_NODELAY, 1)
        self.handle(client_socket)

    cpdef on_close(self, Socket socket):
        if not socket.closed:
            self.pool.put(socket)

    @cython.locals(front_socket=Socket)
    cdef inline handle(self, object socket):
        Connection(self.on_close, self.loop, socket, self.pool.get())

    cpdef start(self):
        self.loop.start()

    cpdef stop(self):
        self.loop.stop(pyev.EVBREAK_ALL)
        self.watcher.stop()
        self.watcher = None
