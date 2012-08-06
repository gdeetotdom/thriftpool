from __future__ import absolute_import
from logging import getLogger
from thriftpool.components.base import Namespace
from thriftpool.controllers.base import Controller

__all__ = ['WorkerController']

logger = getLogger(__name__)


class WorkerNamespace(Namespace):

    name = 'worker'

    def modules(self):
        return ['thriftpool.components.worker.pool']


class WorkerController(Controller):

    Namespace = WorkerNamespace

    def __init__(self):
        self.pool = None
        super(WorkerController, self).__init__()

    def after_start(self):
        for slot in self.app.slots:
            self.pool.register(slot.backend, slot.service.processor)
        super(WorkerController, self).after_start()
