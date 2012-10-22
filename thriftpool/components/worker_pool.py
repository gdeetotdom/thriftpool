from __future__ import absolute_import

import logging

from thriftpool.components.base import StartStopComponent
from thriftpool.utils.functional import cached_property
from thriftpool.utils.logs import LogsMixin
from thriftpool.utils.mixin import SubclassMixin

logger = logging.getLogger(__name__)


class WorkerPool(LogsMixin, SubclassMixin):
    """Maintain pool of hub threads."""

    def __init__(self, app, count=None):
        self.app = app
        self.processors = {}
        self.worker_count = count or 10
        super(WorkerPool, self).__init__()

    @property
    def Worker(self):
        return self.app.socket_zmq.Worker

    @cached_property
    def workers(self):
        return [self.Worker(self.processors) for i in xrange(self.worker_count)]

    def start(self):
        for worker in self.workers:
            worker.start()

    def stop(self):
        for worker in self.workers:
            worker.stop()

    def register(self, slot):
        name, processor = slot.name, slot.service.processor
        self.processors[name] = processor
        self._debug("Register service '%s'.", name)


class WorkerPoolComponent(StartStopComponent):

    name = 'orchestrator.worker_pool'
    requires = ('collector',)

    def create(self, parent):
        worker_pool = parent.worker_pool = WorkerPool(parent.app)
        for slot in parent.app.slots:
            worker_pool.register(slot)
        return worker_pool
