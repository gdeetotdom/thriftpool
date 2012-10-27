"""Contains component that hold listener pool."""
from __future__ import absolute_import

from collections import deque
import logging

from thriftpool.components.base import StartStopComponent
from thriftpool.utils.mixin import LogsMixin
from thriftpool.signals import listener_started, listener_stopped

logger = logging.getLogger(__name__)


class Listeners(LogsMixin):
    """Maintain pool of listeners. When listener starts it open all needed
    sockets and connect to workers. Event loop should be started before
    listeners starts.

    """

    def __init__(self, app):
        self.app = app
        self.pool = deque()
        super(Listeners, self).__init__()

    @property
    def Listener(self):
        """Shortcut to :class:`thriftworker.listener.Listener` class."""
        return self.app.thriftworker.Listener

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
            listener_stopped.send(self, listener=listener, slot=slot,
                                  app=self.app)
            listener.stop()

    def register(self, slot):
        """Register new listener with given parameters."""
        name, host, port, backlog = slot.name, slot.listener.host, \
            slot.listener.port, slot.listener.backlog
        listener = self.Listener(name, (host, port), backlog=backlog)
        self.pool.append((listener, slot))
        self._debug("Register listener for service '%s'.", listener.name)


class ListenersComponent(StartStopComponent):

    name = 'worker.listeners'
    requires = ('services', 'loop')

    def create(self, parent):
        """Create new :class:`ListenerPool` instance. Create existed
        listeners.

        """
        listener_pool = parent.listener_pool = Listeners(parent.app)
        for slot in parent.app.slots:
            listener_pool.register(slot)
        return listener_pool
