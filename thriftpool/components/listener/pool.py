from __future__ import absolute_import
from collections import deque
from thriftpool.components.base import StartStopComponent

__all__ = ['PoolComponent']


class PoolContainer(object):
    """Maintain pool of listeners."""

    def __init__(self, socket_zmq):
        self.socket_zmq = socket_zmq
        self.pool = deque()

    def start(self):
        pass

    def stop(self):
        while self.pool:
            listener = self.pool.popleft()
            listener.stop()

    def register(self, listener):
        self.pool.append(listener)
        listener.start()


class PoolComponent(StartStopComponent):

    name = 'listener.pool'
    requires = ('event_loop',)

    def create(self, parent):
        pool = parent.pool = PoolContainer(parent.socket_zmq)
        return pool
