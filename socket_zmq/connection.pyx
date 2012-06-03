# cython: profile=True
cimport cython
from cpython cimport bool
from socket_zmq.source cimport SocketSource
from socket_zmq.sink cimport ZMQSink


cdef class Connection(object):

    cdef object message

    cdef SocketSource source
    cdef ZMQSink sink

    def __init__(self, source_socket, endpoint_socket):
        self.message = None
        self.source = SocketSource(source_socket, self.on_request)
        self.sink = ZMQSink(endpoint_socket, self.on_response)

    cpdef on_request(self, object message):
        self.message = message
        self.sink.ready(self.message)

    cpdef on_response(self, object message, bool success=True):
        self.source.ready(success, message)
