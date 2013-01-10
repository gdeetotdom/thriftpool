"""Contains component that hold listener pool."""
from __future__ import absolute_import

import logging

from thriftpool.components.base import StartStopComponent
from thriftpool.utils.mixin import LogsMixin
from thriftpool.signals import (listener_started, listener_stopped,
                                listeners_stopped, listeners_started)

logger = logging.getLogger(__name__)


class ListenersComponent(StartStopComponent):

    name = 'manager.listeners'

    def create(self, parent):
        listeners = parent.listeners = parent.app.thriftworker.listeners
        for slot in parent.app.slots:
            name, host, port, backlog = slot.name, slot.listener.host, \
                slot.listener.port, slot.listener.backlog
            listeners.register(name, host, port, backlog)


class ListenersManager(LogsMixin):

    def __init__(self, app, listeners, processes):
        self.app = app
        self.listeners = listeners
        self.processes = processes
        super(ListenersManager, self).__init__()

    def start(self):
        """Start all registered listeners."""
        slots = self.app.slots
        clients = self.processes.clients
        for listener in self.listeners:
            slot = slots[listener.name]
            listener.start()
            listener_started.send(self, listener=listener, slot=slot,
                                  app=self.app)
            clients.spawn(lambda proxy: proxy.start_acceptor(listener.name))
            self._info("Starting listener on '%s:%d' for service '%s'.",
                       listener.host, listener.port, listener.name)
        listeners_started.send(self, app=self.app)

    def stop(self):
        """Stop all registered listeners."""
        slots = self.app.slots
        clients = self.processes.clients
        for listener in self.listeners:
            slot = slots[listener.name]
            self._info("Stopping listening on '%s:%d', service '%s'.",
                       listener.host, listener.port, listener.name)
            listener_stopped.send(self, listener=listener, slot=slot,
                                  app=self.app)
            clients.spawn(lambda proxy: proxy.stop_acceptor(listener.name))
            listener.stop()
        listeners_stopped.send(self, app=self.app)


class ListenersManagerComponent(StartStopComponent):

    name = 'manager.listeners_manager'
    requires = ('loop', 'listeners', 'process_manager')

    def create(self, parent):
        return ListenersManager(parent.app, parent.listeners,
                                parent.processes)
