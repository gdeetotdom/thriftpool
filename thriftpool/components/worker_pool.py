from __future__ import absolute_import

import logging

from thriftpool.components.base import StartStopComponent
from thriftpool.utils.functional import cached_property
from thriftpool.utils.logs import LogsMixin
from thriftpool.utils.mixin import SubclassMixin
from thriftpool.utils.threads import DaemonThread

logger = logging.getLogger(__name__)


class WorkerContainer(DaemonThread):

    def __init__(self, worker):
        self.worker = worker
        super(WorkerContainer, self).__init__()

    def body(self):
        self.worker.start()

    def stop(self):
        self.worker.stop()
        super(WorkerContainer, self).stop()


class WorkerPool(LogsMixin, SubclassMixin):
    """Maintain pool of hub threads."""

    WorkerContainer = WorkerContainer

    def __init__(self, app):
        self.app = app
        self.processors = {}
        super(WorkerPool, self).__init__()

    @property
    def Worker(self):
        return self.app.socket_zmq.Worker

    @cached_property
    def _hubs(self):
        return [self.WorkerContainer(self.Worker(self.processors))
                for i in xrange(10)]

    def start(self):
        for hub in self._hubs:
            hub.start()

    def stop(self):
        for hub in self._hubs:
            hub.stop()

    def register(self, name, processor):
        self._info("Register service '%s'.", name)
        self.processors[name] = processor


class WorkerPoolComponent(StartStopComponent):

    name = 'orchestrator.pool'
    requires = ('device',)

    def create(self, parent):
        worker_pool = parent.worker_pool = WorkerPool(parent.app)
        return worker_pool
