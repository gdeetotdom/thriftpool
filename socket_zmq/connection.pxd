from cpython cimport bool
from socket_zmq.source cimport SocketSource
from socket_zmq.sink cimport ZMQSink


cdef class Connection:

    cdef SocketSource source
    cdef ZMQSink sink

    cdef on_request(self, object message)
    cdef on_response(self, object message, bool success=*)
    cdef close(self)
