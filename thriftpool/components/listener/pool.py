from __future__ import absolute_import
from collections import deque
from thriftpool.components.base import StartStopComponent
from thriftpool.utils.logs import LogsMixin
import logging

__all__ = ['PoolComponent']

logger = logging.getLogger(__name__)


class PoolContainer(LogsMixin):
    """Maintain pool of listeners."""

    def __init__(self):
        self.pool = deque()

    def start(self):
        pass

    def stop(self):
        while self.pool:
            listener = self.pool.popleft()
            self._info("Stopping listening on '%s:%d', service '%s'.",
                       listener.host, listener.port, listener.name)
            listener.stop()

    def register(self, listener):
        self.pool.append(listener)
        self._info("Starting listening on '%s:%d', service '%s'.",
                   listener.host, listener.port, listener.name)
        listener.start()


class PoolComponent(StartStopComponent):

    name = 'listener.pool'
    requires = ('event_loop', 'device')

    def create(self, parent):
        pool = parent.pool = PoolContainer()
        return pool
