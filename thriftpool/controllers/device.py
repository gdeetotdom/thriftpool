from __future__ import absolute_import
from logging import getLogger
from thriftpool.components.base import Namespace
from thriftpool.controllers.base import NestedController

__all__ = ['DeviceController']

logger = getLogger(__name__)


class DeviceNamespace(Namespace):

    name = 'device'

    def modules(self):
        return ['thriftpool.components.device.device']


class DeviceController(NestedController):

    Namespace = DeviceNamespace

    def __init__(self, frontend_endpoint, backend_endpoint):
        self.frontend_endpoint = frontend_endpoint
        self.backend_endpoint = backend_endpoint
        super(DeviceController, self).__init__()
