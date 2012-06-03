# cython: profile=False
cimport cython
from cpython cimport bool
from socket_zmq.source import SocketSource
from socket_zmq.sink import ZMQSink


cdef class Connection(object):

    cdef object message

    cdef object source
    cdef object sink

    def __init__(self, source_socket, endpoint_socket):
        self.message = None
        self.source = SocketSource(source_socket, self.on_request)
        self.sink = ZMQSink(endpoint_socket, self.on_response)

    def on_request(self, message):
        self.message = message
        self.sink.ready(self.message)

    def on_response(self, message, success=True):
        self.source.ready(success, message)
