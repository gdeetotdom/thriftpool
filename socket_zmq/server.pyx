# cython: profile=True
import cython
from gevent.hub import get_hub
from gevent.event import Event
from gevent.socket import EWOULDBLOCK
from gevent.core import MAXPRI, MINPRI
from socket_zmq.connection cimport Connection
from zmq.core.socket cimport Socket
import zmq
import _socket


cdef class StreamServer(object):

    def __init__(self, object context, object frontend, object socket):
        self.io = get_hub().loop.io
        self.socket = socket._sock
        self.context = context
        self.frontend = frontend
        self.stop_wait = Event()
        self.watcher = self.io(self.socket.fileno(), 1, priority=MINPRI)
        self.watcher.start(self.on_connection)

    @cython.locals(front_socket=Socket)
    cdef inline Socket create_backend(self):
        front_socket = self.context.socket(zmq.REQ)
        front_socket.connect(self.frontend)
        return front_socket

    cpdef on_connection(self):
        try:
            client_socket, address = self.socket.accept()
        except _socket.error, err:
            if err[0] == EWOULDBLOCK:
                return
            raise
        client_socket.setblocking(0)
        self.handle(client_socket, address)

    @cython.locals(front_socket=Socket)
    cpdef handle(self, object socket, object address):
        front_socket = self.create_backend()
        connection = Connection(self.io, socket, front_socket)

    cpdef serve_forever(self):
        self.stop_wait.wait()

    cpdef stop(self):
        self.watcher.stop()
        self.stop_wait.set()
