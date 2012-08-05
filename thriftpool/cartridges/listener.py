from .base import ControllerCartridge
from socket_zmq.utils import cached_property
from socket_zmq.app import SocketZMQ

__all__ = ['ListenerCartridge']


class ListenerCartridge(ControllerCartridge):

    @cached_property
    def socket_zmq(self):
        return SocketZMQ(debug=self.app.config.DEBUG)

    def create(self):
        return self.app.ListenerController(self.socket_zmq)

    def listen_for(self, frontend, backend):
        listener = self.socket_zmq.Listener(frontend, backend)
        self.controller.pool.add(listener)
