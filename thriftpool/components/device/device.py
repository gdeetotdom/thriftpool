from __future__ import absolute_import
from thriftpool.components.base import StartStopComponent
from thriftpool.utils.functional import cached_property
from thriftpool.utils.logs import LogsMixin
from thriftpool.utils.other import cpu_count
from thriftpool.utils.threads import DaemonThread
from zmq.core import device
import logging
import zmq

__all__ = ['DeviceComponent']

logger = logging.getLogger(__name__)


class DeviceContainer(LogsMixin, DaemonThread):
    """Run device in separate thread."""

    def __init__(self, frontend_endpoint, backend_endpoint):
        self.frontend_endpoint = frontend_endpoint
        self.backend_endpoint = backend_endpoint
        super(DeviceContainer, self).__init__()

    @cached_property
    def context(self):
        return zmq.Context(cpu_count())

    @cached_property
    def frontend_socket(self):
        socket = self.context.socket(zmq.ROUTER)
        socket.bind(self.frontend_endpoint)
        return socket

    @cached_property
    def backend_socket(self):
        socket = self.context.socket(zmq.DEALER)
        socket.bind(self.backend_endpoint)
        return socket

    def body(self):
        self._debug('Starting device...')
        try:
            device(zmq.QUEUE, self.frontend_socket, self.backend_socket)
        except zmq.ZMQError as exc:
            if exc.errno != zmq.ENOTSOCK and \
                exc.strerror != 'Context was terminated':
                raise
        self._debug('Device stopped...')

    def stop(self):
        self.frontend_socket.close()
        self.backend_socket.close()
        self.context.term()
        super(DeviceContainer, self).stop()


class DeviceComponent(StartStopComponent):

    name = 'device.device'

    def create(self, parent):
        return DeviceContainer(parent.frontend_endpoint,
                               parent.backend_endpoint)
