from __future__ import absolute_import
from thriftpool.components.base import StartStopComponent

__all__ = ['PoolComponent']


class PoolComponent(StartStopComponent):

    name = 'orchestrator.pool'
    requires = ('broker',)

    def create(self, parent):
        pool = parent.pool = parent.app.PoolController()
        return pool
