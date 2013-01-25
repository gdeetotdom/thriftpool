from __future__ import absolute_import

import logging
from signal import SIGTERM

from pyuv import Timer

from thriftworker.utils.loop import in_loop
from thriftworker.utils.mixin import LoopMixin
from thriftworker.utils.decorators import cached_property

from thriftpool.utils.mixin import LogsMixin

from .base import StartStopComponent

logger = logging.getLogger(__name__)


class Watcher(LogsMixin, LoopMixin):

    #: How often (in seconds) we should check for process lifetime?
    resolution = 1.0

    #: Minimum repeat delay.
    repeat_delay = 60.0

    def __init__(self, app, processes):
        self.app = app
        self.processes = processes
        super(Watcher, self).__init__()

    def _loop_cb(self, handle):
        if not self.processes.initialized:
            return
        self._timer.repeat = self.resolution
        processes = self.processes
        now = self.loop.now()
        ttl = self.app.config.WORKER_TTL
        for process_id in sorted(processes):
            lifetime = (now - processes.get_start_time(process_id)) // 1000
            if ttl < lifetime:
                self._info('Send SIGTERM to %d...', process_id)
                self.app.gaffer_manager.send_signal(process_id, SIGTERM)
                self._timer.repeat = self.repeat_delay
                break

    @cached_property
    def _timer(self):
        return Timer(self.loop)

    @in_loop
    def start(self):
        if self.app.config.WORKER_TTL is None:
            return
        self._timer.start(self._loop_cb, self.repeat_delay, self.resolution)

    @in_loop
    def stop(self):
        if not self._timer.closed:
            self._timer.close()


class WatcherComponent(StartStopComponent):

    name = 'manager.watcher'
    requires = ('loop', 'process_manager')

    def create(self, parent):
        return Watcher(parent.app, parent.processes)
