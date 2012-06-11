# cython: profile=True
cimport cython
from cpython cimport bool
from socket_zmq.source cimport SocketSource
from socket_zmq.sink cimport ZMQSink


cdef class Connection(object):

    def __init__(self, io, source_socket, endpoint_socket):
        self.source = SocketSource(io, source_socket, self)
        self.sink = ZMQSink(io, endpoint_socket, self)

    cdef on_request(self, object message):
        self.sink.ready(message)

    cdef on_response(self, object message, bool success=True):
        self.source.ready(success, message)

    cdef close(self):
        if not self.source.is_closed():
            self.source.close()
        if not self.sink.is_closed():
            self.sink.close()
