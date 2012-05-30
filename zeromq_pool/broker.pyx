# cython: profile=True
from collections import deque
from gevent.greenlet import Greenlet, GreenletExit
from gevent.pool import Group
from gevent_zeromq import zmq
from zmq.core.message cimport Frame
from libcpp.list cimport list
from cpython cimport Py_DECREF, Py_INCREF
import cython
from cython.operator cimport (dereference as deref,
                              preincrement as inc,
                              predecrement as dec)


@cython.final
cdef class Device(object):

    cdef list[Frame] *buffer
    cdef object source_socket
    cdef object destination_socket
    cdef object container

    def __cinit__(self):
        self.buffer = new list[Frame]()

    def __init__(self, source_socket, destination_socket, container):
        self.source_socket = source_socket
        self.destination_socket = destination_socket
        self.container = container

    def __dealloc__(self):
        self.buffer.clear()
        del self.buffer

    cdef inline void send(self, object socket, Frame frame, int flags):
        socket.send(frame, flags, copy=False, track=False)
        Py_DECREF(frame)

    cdef inline void send_multipart(self, object socket):
        assert self.buffer.size() > 0
        cdef list[Frame].iterator it = self.buffer.begin()
        cdef list[Frame].iterator last = dec(self.buffer.end())
        while it != last:
            self.send(socket, deref(it), zmq.SNDMORE)
            inc(it)
        self.send(socket, deref(last), 0)

    cdef inline Frame recv(self, object socket):
        frame = socket.recv(copy=False, track=False)
        Py_INCREF(frame)
        return frame

    cdef inline void recv_multipart(self, object socket):
        assert self.buffer.size() == 0
        self.buffer.push_back(self.recv(socket))
        while socket.getsockopt(zmq.RCVMORE):
            self.buffer.push_back(self.recv(socket))

    cpdef loop(self):
        while bool(self.container):
            self.recv_multipart(self.source_socket)
            self.send_multipart(self.destination_socket)
            self.buffer.clear()


class DeviceContainer(Greenlet):

    def __init__(self, source_socket, destination_socket):
        self.source_socket = source_socket
        self.destination_socket = destination_socket
        self.device = Device(source_socket, destination_socket, self)
        Greenlet.__init__(self)

    def _run(self):
        try:
            self.device.loop()
        except GreenletExit:
            pass


class Broker(Greenlet):

    def __init__(self, frontend_socket, backend_socket):
        self.frontend_socket = frontend_socket
        self.backend_socket = backend_socket
        self.frontend_device = DeviceContainer(self.frontend_socket,
                                               self.backend_socket)
        self.backend_device = DeviceContainer(self.backend_socket,
                                              self.frontend_socket)
        self.group = Group()
        self.group.add(self.frontend_device)
        self.group.add(self.backend_device)
        Greenlet.__init__(self)

    def _run(self):
        self.frontend_device.start()
        self.backend_device.start()
        try:
            self.group.join()
        except GreenletExit:
            self.stop()
            self.group.join()

    def stop(self):
        for greenlet in self.group.greenlets:
            if bool(greenlet):
                greenlet.kill()
