from __future__ import absolute_import
from thriftpool.components.base import StartStopComponent
from thriftpool.utils.functional import cached_property
from thriftpool.utils.logs import LogsMixin
from thriftpool.utils.threads import DaemonThread
from zmq.core import device
import logging
import zmq

__all__ = ['DeviceComponent']

logger = logging.getLogger(__name__)


class DeviceContainer(LogsMixin, DaemonThread):
    """Run device in separate thread."""

    def __init__(self, app, frontend, backend):
        self.app = app
        self.frontend = frontend
        self.backend = backend
        super(DeviceContainer, self).__init__()

    @property
    def context(self):
        return self.app.context

    @cached_property
    def frontend_socket(self):
        socket = self.context.socket(zmq.ROUTER)
        socket.bind(self.frontend)
        return socket

    @cached_property
    def backend_socket(self):
        socket = self.context.socket(zmq.DEALER)
        socket.bind(self.backend)
        return socket

    def body(self):
        try:
            device(zmq.QUEUE, self.frontend_socket, self.backend_socket)
        except zmq.ZMQError as exc:
            if exc.errno != zmq.ENOTSOCK:
                raise

    def stop(self):
        self.frontend_socket.close()
        self.backend_socket.close()
        super(DeviceContainer, self).stop()


class DeviceComponent(StartStopComponent):

    name = 'device.device'

    def create(self, parent):
        return DeviceContainer(parent.app,
                               parent.frontend_endpoint,
                               parent.backend_endpoint)
