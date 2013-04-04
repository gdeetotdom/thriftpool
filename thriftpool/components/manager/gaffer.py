"""Start and stop gaffer manager."""
from __future__ import absolute_import

import logging

from thriftworker.utils.mixin import LoopMixin
from thriftworker.utils.loop import in_loop, loop_delegate

from thriftpool.components.base import StartStopComponent
from thriftpool.components.utils import Waiter

logger = logging.getLogger(__name__)


class GafferControl(LoopMixin):
    """Start and stop gaffer."""

    def __init__(self, app):
        self.app = app

        self._stop_waiter = Waiter(
            timeout=self.app.config.PROCESS_STOP_TIMEOUT * 2)

        super(GafferControl, self).__init__()

    @in_loop
    def start(self):
        self.app.gaffer_manager.start()

    def stop(self):
        stop_waiter = self._stop_waiter

        @loop_delegate
        def async_stop():
            self.app.gaffer_manager.stop(
                callback=lambda *args: stop_waiter.done())

        async_stop()
        stop_waiter.wait_or_terminate('Timeout happened when stopping gaffer.')

    def abort(self):
        self._stop_waiter.abort()


class GafferComponent(StartStopComponent):

    name = 'manager.gaffer'
    requires = ('loop',)

    def create(self, parent):
        return GafferControl(parent.app)
