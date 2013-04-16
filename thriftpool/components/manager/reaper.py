"""Periodically restart workers."""
from __future__ import absolute_import

import logging

from pyuv import Timer

from thriftworker.utils.loop import in_loop
from thriftworker.utils.mixin import LoopMixin
from thriftworker.utils.decorators import cached_property

from thriftpool.utils.mixin import LogsMixin
from thriftpool.components.base import StartStopComponent

logger = logging.getLogger(__name__)


class Reaper(LogsMixin, LoopMixin):

    #: How often (in seconds) we should check for process lifetime?
    resolution = 1.0

    def __init__(self, app, processes):
        self.app = app
        self.processes = processes
        super(Reaper, self).__init__()

    @property
    def ttl(self):
        """Process time to live."""
        return self.app.config.WORKER_TTL

    @property
    def repeat_delay(self):
        """Prevent to frequent process reaping."""
        return self.app.config.WORKER_REAP_DELAY

    def _loop_cb(self, handle):
        self._timer.repeat = self.resolution
        processes = self.processes
        if not processes.is_ready() or not len(processes):
            # Not process to reap or to early to reap.
            return
        # Always get first process id.
        process_id = sorted(processes)[0]
        lifetime = (self.loop.now() - processes[process_id].startup_time) // 1000
        if self.ttl > lifetime:
            # Time not come, maybe later.
            return
        self._info('Reap process %d after %d seconds...', process_id, lifetime)
        processes.eliminate(process_id)
        self._timer.repeat = self.repeat_delay

    @cached_property
    def _timer(self):
        return Timer(self.loop)

    @_timer.deleter
    def _timer(self, handle):
        if not handle.closed:
            handle.close()

    @in_loop
    def start(self):
        if self.ttl is None:
            return
        self._timer.start(self._loop_cb, self.repeat_delay, self.resolution)

    @in_loop
    def stop(self):
        del self._timer


class ReaperComponent(StartStopComponent):

    name = 'manager.reaper'
    requires = ('loop', 'processes')

    def create(self, parent):
        return Reaper(parent.app, parent.processes)
