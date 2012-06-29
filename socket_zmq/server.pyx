import cython
import errno
from socket_zmq.sink cimport ZMQSink
from socket_zmq.source cimport SocketSource
from zmq.core.socket cimport Socket
from zmq.core.context cimport Context
from collections import deque
import zmq
import _socket
import pyev
import signal
from pyev import EV_READ, EV_MINPRI, Io

NONBLOCKING = (errno.EAGAIN, errno.EWOULDBLOCK)


cdef class SinkPool(object):

    def __init__(self, object loop, Context context, object frontend,
                 object size):
        self.loop = loop
        self.size = size
        self.pool = deque()
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

    cdef inline put(self, ZMQSink sink):
        if len(self.pool) >= self.size:
            sink.close()
        else:
            self.pool.append(sink)

    cpdef close(self):
        while self.pool:
            self.pool.pop().close()


cdef class StreamServer(object):

    def __init__(self, object loop, object socket, object context,
                 object frontend, object pool_size=None, object backlog=None):
        self.connections = set()
        self.loop = loop
        self.socket = socket._sock
        self.context = context
        self.pool = SinkPool(self.loop, self.context, frontend,
                             pool_size or 128)
        self.backlog = backlog or 128
        self.watcher = Io(self.socket, EV_READ, self.loop,
                          self.on_connection, priority=EV_MINPRI)

    def on_connection(self, object watcher, object revents):
        while True:
            try:
                result = self.socket.accept()
            except _socket.error, err:
                if err[0] in NONBLOCKING:
                    return
                raise
            client_socket = result[0]
            client_socket.setblocking(0)
            client_socket.setsockopt(_socket.SOL_TCP, _socket.TCP_NODELAY, 1)
            self.connections.add(SocketSource(self.pool, self.loop,
                                              client_socket, result[1],
                                              self.on_close))

    def on_close(self, SocketSource source):
        try:
            self.connections.remove(source)
        except KeyError:
            pass

    def start(self):
        self.socket.listen(self.backlog)
        self.watcher.start()

    def stop(self):
        self.socket.close()
        self.watcher.stop()
        while self.connections:
            self.connections.pop().close()
        self.pool.close()
