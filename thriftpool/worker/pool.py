from __future__ import absolute_import
from thriftpool.worker.abstract import StartStopComponent

__all__ = ['PoolComponent']


class PoolComponent(StartStopComponent):
    name = 'worker.pool'

    def create(self, parent):
        return WorkerPool()


class WorkerPool(object):

    def start(self):
        pass

    def stop(self):
        pass
