cimport cython
from cpython cimport bool
from socket_zmq.source cimport SocketSource
from socket_zmq.sink cimport ZMQSink
from zmq.core.message cimport Frame
from gevent.hub import get_hub


cdef class Connection(object):

    cdef SocketSource source
    cdef ZMQSink sink
    cdef object loop

    def __init__(self, source_socket, endpoint_socket):
        self.loop = get_hub().loop
        self.source = SocketSource(self.loop, source_socket, self.on_request)
        self.sink = ZMQSink(self.loop, endpoint_socket, self.on_response)

    cpdef object on_request(self, bytes message):
        self.sink.ready(message)

    cpdef object on_response(self, bytes message, bool success=True):
        self.source.ready(success, message)

    cdef close(self):
        if not self.source.is_closed():
            self.source.close()
        if not self.sink.is_closed():
            self.sink.close()
