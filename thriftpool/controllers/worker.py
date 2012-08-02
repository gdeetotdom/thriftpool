from __future__ import absolute_import
from logging import getLogger
from thriftpool.components.base import Namespace
from thriftpool.controllers.base import Controller

__all__ = ['WorkerController']

logger = getLogger(__name__)


class WorkerNamespace(Namespace):

    name = 'worker'

    def modules(self):
        return ['thriftpool.components.remote_worker']


class WorkerController(Controller):

    Namespace = WorkerNamespace

    def __init__(self, ident, container):
        self.ident = ident
        self.container = container
        super(WorkerController, self).__init__()

    def on_start(self):
        self.container.on_start()

    def on_shutdown(self):
        self.container.on_stop()
        self.app.hub.stop()
