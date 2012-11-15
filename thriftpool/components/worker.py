from __future__ import absolute_import

from .base import StartStopComponent


class WorkerComponent(StartStopComponent):

    name = 'worker.worker'
    requires = ('loop', 'services')

    def create(self, parent):
        return parent.app.thriftworker.worker
