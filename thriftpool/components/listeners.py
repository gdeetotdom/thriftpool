"""Contains component that hold listener pool."""
from __future__ import absolute_import

import logging

from thriftworker.utils.decorators import cached_property
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
        self._pool = []
        super(Listeners, self).__init__()

    def __iter__(self):
        return iter(self._pool)

    @cached_property
    def Listener(self):
        """Shortcut to :class:`thriftworker.listener.Listener` class."""
        return self.app.thriftworker.Listener

    @cached_property
    def channels(self):
        """Return list of registered channels. Useful to pass them
        to child process.

        """
        return [listener.channel for listener, _ in self._pool]

    @cached_property
    def descriptors(self):
        """Return dictionary of relative file descriptor of each listener."""
        use_mutex = self.app.config.WORKERS > 1
        return {i: (listener.name, self.app.env.Mutex() if use_mutex else None)
                for i, (listener, _) in enumerate(self._pool)}

    def register(self, slot):
        """Register new listener with given parameters."""
        name, host, port, backlog = slot.name, slot.listener.host, \
            slot.listener.port, slot.listener.backlog
        listener = self.Listener(name, (host, port), backlog=backlog)
        self._pool.append((listener, slot))
        del self.channels, self.descriptors
        self._debug("Register listener for service '%s'.", listener.name)


class ListenersComponent(StartStopComponent):

    name = 'manager.listeners'

    def create(self, parent):
        listeners = parent.listeners = Listeners(parent.app)
        for slot in parent.app.slots:
            listeners.register(slot)


class ListenersManager(LogsMixin):

    def __init__(self, app, listeners):
        self.app = app
        self.listeners = listeners
        super(ListenersManager, self).__init__()

    def start(self):
        """Start all registered listeners."""
        for listener, slot in self.listeners:
            listener.start()
            listener_started.send(self, listener=listener, slot=slot,
                                  app=self.app)
            self._info("Starting listener on '%s:%d' for service '%s'.",
                       listener.host, listener.port, listener.name)

    def stop(self):
        """Stop all registered listeners."""
        for listener, slot in self.listeners:
            self._info("Stopping listening on '%s:%d', service '%s'.",
                       listener.host, listener.port, listener.name)
            listener_stopped.send(self, listener=listener, slot=slot,
                                  app=self.app)
            listener.stop()


class ListenersManagerComponent(StartStopComponent):

    name = 'manager.listeners_manager'
    requires = ('loop', 'listeners', 'process_manager')

    def create(self, parent):
        return ListenersManager(parent.app, parent.listeners)
