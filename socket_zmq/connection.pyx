# cython: profile=True
cimport cython
from cpython cimport bool
from socket_zmq.source cimport SocketSource
from socket_zmq.sink cimport ZMQSink


cdef class Connection(object):

    def __init__(self, object on_close, object loop, object source_socket,
                                                    object endpoint_socket):
        self.on_close = on_close
        self.socket = endpoint_socket
        self.source = SocketSource(loop, source_socket, self)
        self.sink = ZMQSink(loop, endpoint_socket, self)

    cdef on_request(self, object message):
        self.sink.ready(message)

    cdef on_response(self, object message, bool success=True):
        self.source.ready(success, message)

    cdef close(self):
        if not self.source.is_closed():
            self.source.close()
        if not self.sink.is_closed():
            self.sink.close()
        self.on_close(self.socket)
