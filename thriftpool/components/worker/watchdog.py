"""Watch for parent process and exit if it die."""
from __future__ import absolute_import

import os
import signal
import logging

from pyuv import Pipe
from pyuv.errno import strerror

from thriftworker.utils.mixin import LoopMixin
from thriftworker.utils.decorators import cached_property
from thriftworker.utils.loop import in_loop

from thriftpool.components.base import StartStopComponent

logger = logging.getLogger(__name__)


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
