from .base import ControllerCartridge
from socket_zmq.utils import cached_property
from socket_zmq.app import SocketZMQ

__all__ = ['WorkerCartridge']


class WorkerCartridge(ControllerCartridge):

    @cached_property
    def socket_zmq(self):
        return SocketZMQ(debug=self.app.config.DEBUG)

    def create(self):
        return self.app.WorkerController(self.socket_zmq)

    def handle(self, backend):
        self.controller.pool.add(backend)
