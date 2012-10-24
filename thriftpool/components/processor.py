from __future__ import absolute_import

import logging

from thriftpool.components.base import StartStopComponent
from thriftpool.utils.mixin import LogsMixin

logger = logging.getLogger(__name__)


class ProcessorComponent(LogsMixin, StartStopComponent):

    name = 'orchestrator.processor'

    def create(self, parent):
        processor = parent.app.socket_zmq.processor
        for slot in parent.app.slots:
            self._debug("Register service '%s'.", slot.name)
            processor.register(slot.name, slot.service.processor)
