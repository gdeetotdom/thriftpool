# cython: profile=True
import cython
import errno
from socket_zmq.connection cimport Connection
from socket_zmq.sink cimport ZMQSink
from zmq.core.socket cimport Socket
from zmq.core.context cimport Context
from collections import deque
import zmq
import _socket
import pyev
import weakref
import signal

NONBLOCKING = (errno.EAGAIN, errno.EWOULDBLOCK)
STOPSIGNALS = (signal.SIGINT, signal.SIGTERM)


cdef class SinkPool(object):

    def __init__(self, object loop, Context context, object frontend):
        self.loop = loop
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
        self.pool.append(sink)

    cpdef close(self):
        while self.pool:
            self.pool.pop().close()


cdef class StreamServer(object):

    def __init__(self, object socket, object context, object frontend):
        self.connections = set()
        self.loop = pyev.Loop()
        self.context = context
        self.socket = socket._sock
        self.pool = SinkPool(self.loop, self.context, frontend)
        self.watchers = [pyev.Io(self.socket, pyev.EV_READ,
                                 self.loop, self.on_connection,
                                 priority=pyev.EV_MINPRI)]
        self.watchers.extend([pyev.Signal(sig, self.loop, self.on_signal)
                              for sig in STOPSIGNALS])

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
            client_socket.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
            self.connections.add(
                Connection(self.pool, self.loop, client_socket, self.on_close))

    def on_signal(self, object watcher, object revents):
        self.stop()

    def on_close(self, Connection connection):
        try:
            self.connections.remove(connection)
        except KeyError:
            pass

    def start(self):
        self.socket.listen(50)
        for watcher in self.watchers:
            watcher.start()
        self.loop.start()

    def stop(self):
        self.loop.stop(pyev.EVBREAK_ALL)
        self.socket.close()
        while self.watchers:
            self.watchers.pop().stop()
        while self.connections:
            self.connections.pop().close()
        self.pool.close()

