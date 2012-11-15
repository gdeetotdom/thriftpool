from __future__ import absolute_import

import logging
from pyuv import Timer

from thriftworker.utils.loop import in_loop
from thriftworker.utils.mixin import LoopMixin
from thriftworker.utils.decorators import cached_property
from thriftpool.utils.mixin import LogsMixin

from .base import StartStopComponent

logger = logging.getLogger(__name__)


class Initiator(LogsMixin, LoopMixin):

    interval = 5.0
    timeout = interval * 6

    def __init__(self, app, controller):
        self.app = app
        self.controller = controller
        self._replies = {}
        super(Initiator, self).__init__()

    @cached_property
    def _timer(self):
        return Timer(self.loop)

    def _on_reply(self, producer, ident):
        self._replies[ident] = (producer.process, self.loop.now())

    def _on_interval(self, handle):
        self.controller.workers.apply('ping', self._on_reply)
        replies = self._replies
        now = self.loop.now()
        for ident, (process, time) in list(replies.items()):
            if not process.active:
                replies.pop(ident)
            elif time + self.timeout * 1000 < now:
                self._critical('Process %d timed out!', process.id)
                process.kill(9)
                replies.pop(ident)

    @in_loop
    def start(self):
        self._timer.start(self._on_interval, timeout=self.interval,
                          repeat=self.interval)

    @in_loop
    def stop(self):
        self._timer.stop()
        self._timer.close()


class WatchdogComponent(StartStopComponent):

    name = 'manager.watchdog'
    requires = ('workers',)

    def create(self, parent):
        return Initiator(parent.app, parent)
