from __future__ import absolute_import

from collections import deque
import logging

from thriftpool.components.base import StartStopComponent
from thriftpool.utils.logs import LogsMixin

logger = logging.getLogger(__name__)


class ListenerPool(LogsMixin):
    """Maintain pool of listeners."""

    def __init__(self, app):
        self.app = app
        self.pool = deque()
        super(ListenerPool, self).__init__()

    @property
    def Listener(self):
        return self.app.socket_zmq.Listener

    def start(self):
        for listener in self.pool:
            listener.start()

    def stop(self):
        while self.pool:
            listener = self.pool.popleft()
            self._info("Stopping listening on '%s:%d', service '%s'.",
                       listener.host, listener.port, listener.name)
            listener.stop()

    def register(self, name, host, port, backlog=None):
        listener = self.Listener(name, (host, port or 0), backlog=backlog)
        self.pool.append(listener)
        self._info("Register listener on '%s:%d' for service '%s'.",
                   listener.host, listener.port, listener.name)


class ListenerPoolComponent(StartStopComponent):

    name = 'orchestrator.listener_pool'
    requires = ('event_loop',)

    def create(self, parent):
        listener_pool = parent.listener_pool = ListenerPool(parent.app)
        for slot in parent.app.slots:
            listener_pool.register(slot.name, slot.listener.host,
                                   slot.listener.port, slot.listener.backlog)
        return listener_pool
