import cython
import errno
from socket_zmq.pool cimport SinkPool
from socket_zmq.source cimport SocketSource
from zmq.core.context cimport Context
import _socket
from pyev import EV_READ, EV_MINPRI, Io

NONBLOCKING = (errno.EAGAIN, errno.EWOULDBLOCK)


cdef class Proxy(object):

    def __init__(self, object loop, object socket, Context context,
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
        self.connections.remove(source)

    def start(self):
        self.socket.listen(self.backlog)
        self.watcher.start()

    def stop(self):
        self.socket.close()
        self.watcher.stop()
        while self.connections:
            self.connections.pop().close()
        self.pool.close()
