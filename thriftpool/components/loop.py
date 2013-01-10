from __future__ import absolute_import

from .base import StartStopComponent


class BaseLoopComponent(StartStopComponent):

    abstract = True

    def create(self, parent):
        return parent.app.thriftworker.hub


class WorkerLoopComponent(BaseLoopComponent):

    name = 'worker.loop'


class ManagerLoopComponent(BaseLoopComponent):

    name = 'manager.loop'
