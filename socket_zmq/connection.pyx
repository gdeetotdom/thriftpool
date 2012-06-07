# cython: profile=True
cimport cython
from cpython cimport bool
from socket_zmq.source cimport SocketSource
from socket_zmq.sink cimport ZMQSink
from zmq.core.message cimport Frame


cdef class Connection(object):

    cdef SocketSource source
    cdef ZMQSink sink

    def __init__(self, source_socket, endpoint_socket):
        self.source = SocketSource(source_socket, self.on_request)
        self.sink = ZMQSink(endpoint_socket, self.on_response)

    cpdef object on_request(self, bytes message):
        self.sink.ready(message)

    cpdef object on_response(self, bytes message, bool success=True):
        self.source.ready(success, message)
