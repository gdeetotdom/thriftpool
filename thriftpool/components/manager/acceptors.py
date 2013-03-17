"""Start acceptors in spawned processes."""
from __future__ import absolute_import

import logging

from thriftpool.components.base import StartStopComponent
from thriftpool.utils.mixin import LogsMixin
from thriftpool.signals import (listener_started, listener_stopped,
                                listeners_stopped, listeners_started)

logger = logging.getLogger(__name__)


class Acceptors(LogsMixin):

    def __init__(self, app, listeners, processes):
        self.app = app
        self.listeners = listeners
        self.processes = processes
        super(Acceptors, self).__init__()

    def start(self):
        """Start all registered listeners."""
        slots = self.app.slots
        broker = self.processes.broker
        for listener in self.listeners:
            slot = slots[listener.name]
            listener.start()
            listener_started.send(self, listener=listener, slot=slot,
                                  app=self.app)
            broker.spawn(lambda proxy: proxy.start_acceptor(listener.name))
            self._info("Starting listener on '%s:%d' for service '%s'.",
                       listener.host, listener.port, listener.name)
        listeners_started.send(self, app=self.app)

    def stop(self):
        """Stop all registered listeners."""
        slots = self.app.slots
        broker = self.processes.broker
        for listener in self.listeners:
            slot = slots[listener.name]
            self._info("Stopping listening on '%s:%d', service '%s'.",
                       listener.host, listener.port, listener.name)
            listener_stopped.send(self, listener=listener, slot=slot,
                                  app=self.app)
            broker.spawn(lambda proxy: proxy.stop_acceptor(listener.name))
            listener.stop()
        listeners_stopped.send(self, app=self.app)


class AcceptorsComponent(StartStopComponent):

    name = 'manager.acceptors'
    requires = ('loop', 'listeners', 'processes')

    def create(self, parent):
        return Acceptors(parent.app, parent.listeners, parent.processes)
