from socket_zmq.server import StreamServer
from zmq.devices import ThreadDevice
import _socket
import pyev
import signal
import socket
import zmq
from itertools import chain

__all__ = ['ServerContainer']


class ServerContainer(object):

    def __init__(self):
        self.loop = pyev.Loop()
        self.context = zmq.Context()
        self.watchers = [pyev.Signal(sig, self.loop, self.on_signal)
                         for sig in (signal.SIGINT, signal.SIGTERM)]
        self.servers = []
        self.devices = []

    def on_signal(self, watcher, revents):
        self.stop()

    def create_listener(self, address):
        """A shortcut to create a TCP socket, bind it and put it into listening
        state.

        """
        sock = socket.socket(family=_socket.AF_INET)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(address)
        sock.setblocking(0)
        return sock

    def create_server(self, address, frontend, pool_size=None, backlog=None):
        server = StreamServer(self.loop, self.create_listener(address),
                              self.context, frontend, pool_size, backlog)
        return server

    def create_device(self, frontend, backend):
        device = ThreadDevice(zmq.QUEUE, zmq.ROUTER, zmq.DEALER)
        device.context_factory = lambda: self.context
        device.bind_in(frontend)
        device.bind_out(backend)
        return device

    def register(self, address, frontend, backend, pool_size=None,
                 backlog=None):
        self.devices.append(self.create_device(frontend, backend))
        self.servers.append(self.create_server(address, frontend, pool_size,
                                               backlog))

    def start(self):
        for resource in chain(self.watchers, self.devices, self.servers):
            resource.start()
        self.loop.start()

    def stop(self):
        self.loop.stop(pyev.EVBREAK_ALL)
        for resources in [self.servers, self.devices, self.watchers]:
            while resources:
                try:
                    resources.pop().stop()
                except AttributeError:
                    pass

    def serve_forever(self):
        try:
            self.start()
        finally:
            self.stop()
