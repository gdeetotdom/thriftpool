# cython: profile=True
import cython
from gevent.hub import get_hub
from gevent.event import Event
from gevent.socket import EWOULDBLOCK
from gevent.core import MAXPRI, MINPRI
from socket_zmq.connection cimport Connection
from zmq.core.socket cimport Socket
from collections import deque
import zmq
import _socket


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
        self.io = get_hub().loop.io
        self.pool = SocketPool(context, frontend)
        self.socket = socket._sock
        self.stop_wait = Event()
        self.watcher = self.io(self.socket.fileno(), 1, priority=MINPRI)
        self.watcher.start(self.on_connection)

    cpdef on_connection(self):
        try:
            client_socket, address = self.socket.accept()
        except _socket.error, err:
            if err[0] == EWOULDBLOCK:
                return
            raise
        client_socket.setblocking(0)
        client_socket.setsockopt(_socket.SOL_TCP, _socket.TCP_NODELAY, 1)
        self.handle(client_socket, address)

    cpdef on_close(self, Socket socket):
        if not socket.closed:
            self.pool.put(socket)

    @cython.locals(front_socket=Socket)
    cdef inline handle(self, object socket, object address):
        Connection(self.on_close, self.io, socket, self.pool.get())

    cpdef serve_forever(self):
        self.stop_wait.wait()

    cpdef stop(self):
        self.watcher.stop()
        self.stop_wait.set()
