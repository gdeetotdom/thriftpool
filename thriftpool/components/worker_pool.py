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

    @property
    def endpoint(self):
        return self.worker.worker_endpoint

    def start(self):
        super(WorkerContainer, self).start()
        self.worker.wait()

    def body(self):
        self.worker.start()

    def stop(self):
        self.worker.stop()
        super(WorkerContainer, self).stop()


class WorkerPool(LogsMixin, SubclassMixin):
    """Maintain pool of hub threads."""

    WorkerContainer = WorkerContainer

    def __init__(self, app, count=None):
        self.app = app
        self.processors = {}
        self.worker_count = count or 10
        super(WorkerPool, self).__init__()

    @property
    def Worker(self):
        return self.app.socket_zmq.Worker

    @cached_property
    def _containers(self):
        return [self.WorkerContainer(self.Worker(self.processors))
                for i in xrange(self.worker_count)]

    @property
    def endpoints(self):
        return [container.endpoint for container in self._containers]

    def start(self):
        for container in self._containers:
            container.start()

    def stop(self):
        for container in self._containers:
            container.stop()

    def register(self, name, processor):
        self._info("Register service '%s'.", name)
        self.processors[name] = processor


class WorkerPoolComponent(StartStopComponent):

    name = 'orchestrator.worker_pool'

    def create(self, parent):
        worker_pool = parent.worker_pool = WorkerPool(parent.app)
        for slot in parent.app.slots:
            worker_pool.register(slot.name, slot.service.processor)
        return worker_pool
