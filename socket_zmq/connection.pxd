from cpython cimport bool
from socket_zmq.source cimport SocketSource
from socket_zmq.sink cimport ZMQSink
from zmq.core.socket cimport Socket
from socket_zmq.server cimport SinkPool


cdef class Connection:

    cdef SocketSource source
    cdef ZMQSink sink
    cdef SinkPool pool
    cdef object on_close

    cpdef on_request(self, object message)
    cpdef on_response(self, object message, bool success=*)
    cpdef close(self)
