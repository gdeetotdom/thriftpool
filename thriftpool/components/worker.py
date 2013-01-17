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


class ServicesComponent(LogsMixin, StartStopComponent):

    name = 'worker.services'

    def create(self, parent):
        services = parent.app.thriftworker.services
        for slot in parent.app.slots:
            self._debug("Register service '%s'.", slot.name)
            services.register(slot.name, slot.service.processor)


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

    @in_loop
    def stop(self):
        pipe = self._pipe
        if pipe.active and not pipe.closed:
            pipe.stop_read()


class WatchdogComponent(StartStopComponent):

    name = 'worker.watchdog'
    requires = ('loop', )

    def create(self, parent):
        return Watchdog(parent.app, parent.handshake_fd)
