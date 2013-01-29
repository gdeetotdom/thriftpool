from __future__ import absolute_import

import os
import signal
import logging

from pyuv import Pipe
from pyuv.errno import strerror

from thriftworker.utils.mixin import LoopMixin
from thriftworker.utils.loop import in_loop
from thriftworker.utils.decorators import cached_property

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


class WorkerComponent(StartStopComponent):

    name = 'worker.worker'
    requires = ('loop', 'services')

    def create(self, parent):
        return parent.app.thriftworker.worker


class AcceptorsComponent(StartStopComponent):

    name = 'worker.acceptors'
    requires = ('loop', 'worker')

    def create(self, parent):
        acceptors = parent.acceptors = parent.app.thriftworker.acceptors
        return acceptors


class Watchdog(LoopMixin):
    """Ensure that given socket alive or stop controller."""

    def __init__(self, app, descriptor):
        self.app = app
        self.descriptor = descriptor
        super(Watchdog, self).__init__()

    def _on_event(self, handle, data, error):
        if error:
            logger.error('Error %r happened on descriptor %d',
                         strerror(error), self.descriptor)
            self._pipe.close()
            # notify us that we should stop
            os.kill(os.getpid(), signal.SIGTERM)

    @cached_property
    def _pipe(self):
        pipe = Pipe(self.loop)
        pipe.open(self.descriptor)
        return pipe

    @in_loop
    def start(self):
        self._pipe.start_read(self._on_event)
        self._pipe.write('x')

    @in_loop
    def stop(self):
        if not self._pipe.closed:
            self._pipe.close()


class WatchdogComponent(StartStopComponent):

    name = 'worker.watchdog'
    requires = ('loop', )

    def create(self, parent):
        return Watchdog(parent.app, parent.handshake_fd)
