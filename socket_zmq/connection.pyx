# cython: profile=True
cimport cython
from cpython cimport bool
from socket_zmq.source cimport SocketSource
from socket_zmq.sink cimport ZMQSink
from socket_zmq.server cimport SinkPool


cdef class Connection(object):

    def __init__(self, SinkPool pool, object loop, object source_socket,
                 object on_close):
        self.pool = pool
        self.on_close = on_close

        self.source = SocketSource(loop, source_socket)
        self.source.bound(self)

        self.sink = self.pool.get()
        self.sink.bound(self)

    cpdef on_request(self, object message):
        self.sink.ready(message)

    cpdef on_response(self, object message, bool success=True):
        self.source.ready(success, message)

    cpdef close(self):
        if not self.source.is_closed():
            self.source.close()
        self.source.unbound()

        if self.sink.is_ready():
            self.pool.put(self.sink)
        elif not self.sink.is_closed():
            self.sink.close()
        self.sink.unbound()

        self.sink = self.source = self.pool = None
        self.on_close(self)
