cimport cython
from cpython cimport bool
from socket_zmq.source cimport SocketSource
from socket_zmq.sink cimport ZMQSink
from gevent.hub import get_hub


cdef class Connection(object):

    def __init__(self, source_socket, endpoint_socket):
        self.loop = get_hub().loop
        self.source = SocketSource(self.loop, source_socket, self)
        self.sink = ZMQSink(self.loop, endpoint_socket, self)

    cdef void on_request(self, object message) except *:
        self.sink.ready(message)

    cdef void on_response(self, bytes message, bool success=True) except *:
        self.source.ready(success, message)

    cdef close(self):
        if not self.source.is_closed():
            self.source.close()
        if not self.sink.is_closed():
            self.sink.close()
