"""Contains component that hold listener pool."""
from __future__ import absolute_import

import logging

from thriftpool.components.base import StartStopComponent

logger = logging.getLogger(__name__)


class ListenersComponent(StartStopComponent):

    name = 'manager.listeners'

    def create(self, parent):
        listeners = parent.listeners = parent.app.thriftworker.listeners
        for slot in parent.app.slots:
            name, host, port, backlog = slot.name, slot.listener.host, \
                slot.listener.port, slot.listener.backlog
            listeners.register(name, host, port, backlog)
