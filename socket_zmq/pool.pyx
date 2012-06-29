from collections import deque
import cython
from socket_zmq.sink cimport ZMQSink
from zmq.core.context cimport Context
from zmq.core.socket cimport Socket
from zmq import REQ


cdef class SinkPool(object):

    def __init__(self, object loop, Context context, object frontend,
                 object size):
        self.loop = loop
        self.size = size
        self.pool = deque()
        self.context = context
        self.frontend = frontend

    @cython.locals(front_socket=Socket, sink=ZMQSink)
    cdef inline ZMQSink create(self):
        front_socket = self.context.socket(REQ)
        front_socket.connect(self.frontend)
        sink = ZMQSink(self.loop, front_socket)
        return sink

    @cython.locals(sink=ZMQSink)
    cdef inline ZMQSink get(self):
        try:
            sink = self.pool.popleft()
        except IndexError:
            sink = self.create()
        return sink

    cdef inline put(self, ZMQSink sink):
        if len(self.pool) >= self.size:
            sink.close()
        else:
            self.pool.append(sink)

    cpdef close(self):
        while self.pool:
            self.pool.pop().close()
