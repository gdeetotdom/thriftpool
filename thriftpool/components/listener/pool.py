from __future__ import absolute_import
from collections import deque
from thriftpool.components.base import StartStopComponent
from thriftpool.utils.logs import LogsMixin
import logging

__all__ = ['PoolComponent']

logger = logging.getLogger(__name__)


class PoolContainer(LogsMixin):
    """Maintain pool of listeners."""

    def __init__(self, socket_zmq):
        self.socket_zmq = socket_zmq
        self.pool = deque()

    def start(self):
        pass

    def stop(self):
        while self.pool:
            listener = self.pool.popleft()
            logger.info("Stopping listening on '%s:%d'.", listener.host, listener.port)
            listener.stop()

    def register(self, name, listener):
        self.pool.append(listener)
        logger.info("Starting listening on '%s:%d', service '%s'.", listener.host,
                    listener.port, name)
        listener.start()


class PoolComponent(StartStopComponent):

    name = 'listener.pool'
    requires = ('event_loop',)

    def create(self, parent):
        pool = parent.pool = PoolContainer(parent.socket_zmq)
        return pool
