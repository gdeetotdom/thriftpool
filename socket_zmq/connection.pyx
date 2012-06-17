# cython: profile=True
cimport cython
from cpython cimport bool
from socket_zmq.source cimport SocketSource
from socket_zmq.sink cimport ZMQSink


cdef class Connection(object):

    def __init__(self, object on_close, object loop, object source_socket,
                                                    ZMQSink sink):
        self.on_close = on_close
        self.source = SocketSource(loop, source_socket, self)
        self.sink = sink
        self.sink.on_response = self.on_response

    cpdef on_request(self, object message):
        self.sink.ready(message)

    cpdef on_response(self, object message, bool success=True):
        self.source.ready(success, message)

    cdef close(self):
        if not self.source.is_closed():
            self.source.close()
        self.sink.on_response = None
        self.on_close(self.sink)
