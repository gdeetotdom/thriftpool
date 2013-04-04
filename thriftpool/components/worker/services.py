from __future__ import absolute_import

import logging

from thriftpool.components.base import StartStopComponent
from thriftpool.utils.mixin import LogsMixin

logger = logging.getLogger(__name__)


class ServicesManager(LogsMixin):

    def __init__(self, slots, services):
        self.slots = slots
        self.services = services
        super(ServicesManager, self).__init__()

    def start(self):
        for name in self.services:
            self.slots[name].start()

    def stop(self):
        for name in self.services:
            self.slots[name].stop()

    def register(self, name, processor):
        self._debug("Register service '%s'.", name)
        self.services.register(name, processor)


class ServicesComponent(StartStopComponent):

    name = 'worker.services'

    def create(self, parent):
        services = parent.app.thriftworker.services
        manager = ServicesManager(parent.app.slots, services)
        for slot in parent.app.slots:
            manager.register(slot.name, slot.service.processor)
        return manager
