from __future__ import absolute_import

from .base import StartStopComponent


class DeviceProxy(object):
    """Proxy to :class:`socket_zmq.device.Device`.

    We should create all instance as later as possible.

    """

    def __init__(self, app):
        self.app = app

    @property
    def device(self):
        """Get instance of device."""
        return self.app.socket_zmq.device

    def start(self):
        self.device.start()

    def stop(self):
        self.device.stop()


class DeviceComponent(StartStopComponent):

    name = 'orchestrator.device'

    def create(self, parent):
        return DeviceProxy(parent.app)
