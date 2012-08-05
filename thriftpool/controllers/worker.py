from __future__ import absolute_import
from logging import getLogger
from thriftpool.components.base import Namespace
from thriftpool.controllers.base import NestedController

__all__ = ['WorkerController']

logger = getLogger(__name__)


class WorkerNamespace(Namespace):

    name = 'worker'

    def modules(self):
        return ['thriftpool.components.worker.pool']


class WorkerController(NestedController):

    Namespace = WorkerNamespace

    def __init__(self, socket_zmq):
        self.socket_zmq = socket_zmq
        self.pool = None
        super(WorkerController, self).__init__()
