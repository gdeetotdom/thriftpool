# cython: profile=True
cimport cython
from zmq.core.socket cimport Socket
from zmq.core.context cimport Context
from collections import deque
from zmq.core.constants import (NOBLOCK, EAGAIN, FD, EVENTS, POLLIN, POLLOUT,
    RCVMORE, SNDMORE)
from zmq.core.error import ZMQError
import pyev
import zmq


cdef class Relay(object):

    def __init__(self, object loop, Socket source, Socket sink):
        self.buffer = deque()
        self.source = source
        self.sink = sink
        self.watcher = pyev.Io(self.source.getsockopt(FD), pyev.EV_READ,
                               loop, self.on_read,
                               priority=pyev.EV_MAXPRI)
        self.watcher.start()

    @cython.locals(events=cython.int)
    cpdef on_read(self, object watcher, object revents):
        msg = None
        flags = 0
        try:

            while True:
                events = self.source.getsockopt(EVENTS)
                if events & POLLIN:
                    msg = self.source.recv(NOBLOCK)
                    flags = SNDMORE if self.source.getsockopt(RCVMORE) else 0

                if msg is None:
                    break

                events = self.sink.getsockopt(EVENTS)
                if events & POLLOUT:
                    self.sink.send(msg, flags)
                    msg = None
                    flags = 0

        except ZMQError, e:
            if e.errno != EAGAIN:
                pass
            raise


cdef class Device(object):

    def __init__(self, object loop, Context context, object frontend, object backend):
        self.loop = loop
        self.context = context
        self.frontend = frontend
        self.backend = backend
        self.frontend_socket = self.context.socket(zmq.ROUTER)
        self.backend_socket = self.context.socket(zmq.DEALER)
        self.frontend_relay = self.backend_relay = None

    def start(self):
        self.frontend_socket.bind(self.frontend)
        self.backend_socket.bind(self.backend)
        self.frontend_relay = Relay(self.loop,
                                    self.frontend_socket, self.backend_socket)
        self.backend_relay = Relay(self.loop,
                                   self.backend_socket, self.frontend_socket)

    def stop(self):
        pass
