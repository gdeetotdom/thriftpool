# cython: profile=True
import cython
from errno import EWOULDBLOCK
from socket_zmq.connection cimport Connection
from socket_zmq.sink cimport ZMQSink
from socket_zmq.device cimport Device
from zmq.core.socket cimport Socket
from zmq.core.context cimport Context
from collections import deque
import zmq
import _socket
import pyev
import weakref


cdef class SinkPool(object):

    def __init__(self, object loop, Context context, object frontend,
                 object size=128):
        self.loop = loop
        self.pool = deque(maxlen=size)
        self.context = context
        self.frontend = frontend

    @cython.locals(front_socket=Socket, sink=ZMQSink)
    cdef inline ZMQSink create(self):
        front_socket = self.context.socket(zmq.REQ)
        front_socket.connect(self.frontend)
        sink = ZMQSink(self.loop, front_socket)
        return sink

    @cython.locals(sink=ZMQSink)
    cdef inline ZMQSink get(self):
        try:
            sink = self.pool.popleft()
        except IndexError:
            sink = self.create()
        return sink

    cdef inline void put(self, ZMQSink sink) except *:
        self.pool.append(sink)


cdef class StreamServer(object):

    def __init__(self, socket, context, frontend, backend):
        self.loop = pyev.Loop()
        self.context = context
        self.device = Device(self.loop, self.context, frontend, backend)
        self.pool = SinkPool(self.loop, self.context, frontend)
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

    cpdef on_close(self, ZMQSink sink):
        if not sink.is_ready():
            sink.close()
        else:
            self.pool.put(sink)

    cdef inline handle(self, object socket):
        Connection(self.on_close, self.loop, socket, self.pool.get())

    cpdef start(self):
        self.device.start()
        self.loop.start()

    cpdef stop(self):
        self.loop.stop(pyev.EVBREAK_ALL)
        self.socket.close()
        self.device.stop()
        self.watcher.stop()
        self.watcher = None
