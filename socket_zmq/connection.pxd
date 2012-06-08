from cpython cimport bool
from socket_zmq.source cimport SocketSource
from socket_zmq.sink cimport ZMQSink


cdef class Connection:

    cdef SocketSource source
    cdef ZMQSink sink
    cdef object loop

    cdef void on_request(self, object message) except *
    cdef void on_response(self, bytes message, bool success=?) except *
    cdef close(self)
