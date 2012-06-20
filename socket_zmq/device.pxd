from zmq.core.socket cimport Socket
from zmq.core.context cimport Context


cdef class Relay(object):

    cdef object buffer
    cdef object watcher
    cdef Socket source
    cdef Socket sink

    cpdef on_read(self, object watcher, object revents)


cdef class Device(object):

    cdef object loop
    cdef Context context

    cdef object frontend
    cdef object backend

    cdef Socket frontend_socket
    cdef Socket backend_socket

    cdef Relay frontend_relay
    cdef Relay backend_relay
