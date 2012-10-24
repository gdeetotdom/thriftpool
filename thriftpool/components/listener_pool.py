"""Contains component that hold listener pool."""
from __future__ import absolute_import

from collections import deque
import logging

from thriftpool.components.base import StartStopComponent
from thriftpool.utils.logs import LogsMixin
from thriftpool.signals import listener_started, listener_stopped

logger = logging.getLogger(__name__)


class ListenerPool(LogsMixin):
    """Maintain pool of listeners. When listener starts it open all needed
    sockets and connect to workers. Event loop should be started before
    listeners starts.

    """

    def __init__(self, app):
        self.app = app
        self.pool = deque()
        super(ListenerPool, self).__init__()

    @property
    def Listener(self):
        """Shortcut to :class:`socket_zmq.listener.Listener` class."""
        return self.app.socket_zmq.Listener

    def start(self):
        """Start all registered listeners."""
        for listener, slot in self.pool:
            listener.start()
            listener_started.send(self, listener=listener, slot=slot,
                                  app=self.app)
            self._info("Starting listener on '%s:%d' for service '%s'.",
                       listener.host, listener.port, listener.name)

    def stop(self):
        """Stop all registered listeners."""
        for listener, slot in self.pool:
            self._info("Stopping listening on '%s:%d', service '%s'.",
                       listener.host, listener.port, listener.name)
            listener.stop()
            listener_stopped.send(self, listener=listener, slot=slot,
                                  app=self.app)

    def register(self, slot):
        """Register new listener with given parameters."""
        name, host, port, backlog = slot.name, slot.listener.host, \
            slot.listener.port, slot.listener.backlog
        listener = self.Listener(name, (host, port), backlog=backlog)
        self.pool.append((listener, slot))
        self._debug("Register listener for service '%s'.", listener.name)


class ListenerPoolComponent(StartStopComponent):

    name = 'orchestrator.listener_pool'
    requires = ('processor', 'event_loop')

    def create(self, parent):
        """Create new :class:`ListenerPool` instance. Create existed
        listeners.

        """
        listener_pool = parent.listener_pool = ListenerPool(parent.app)
        for slot in parent.app.slots:
            listener_pool.register(slot)
        return listener_pool
