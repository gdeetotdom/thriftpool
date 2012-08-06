from __future__ import absolute_import
from billiard import Process
from billiard.common import restart_state
from billiard.pool import LaxBoundedSemaphore, EX_OK, WorkersJoined
from collections import deque
from logging import getLogger
from thriftpool.components.base import StartStopComponent
from thriftpool.utils.proctitle import setproctitle
import itertools

__all__ = ['PoolComponent']

logger = getLogger(__name__)


class BoundedProcess(Process):
    """Process that will execute given controller."""

    def __init__(self, controller, num=0):
        self.controller = controller
        super(BoundedProcess, self).__init__(
            name="{0}-{1}".format(type(self.controller).__name__, num))

    def run(self):
        setproctitle('[{0}]'.format(self.name))
        self.controller.start()


class Pool(object):
    """Spawn and maintain worker pool."""

    Process = BoundedProcess

    def __init__(self):
        self._pool = []
        self._queue = deque()
        self._processes = 0
        self._next_number = itertools.count()
        self.restart_state = restart_state(5, 1)
        self._putlock = LaxBoundedSemaphore(self._processes)

    def _create_worker_process(self):
        p = self.Process(self._queue.popleft(), self._next_number.next())
        self._pool.append(p)
        p.daemon = True
        p.start()

    def _join_exited_workers(self, shutdown=False):
        """Cleanup after any worker processes which have exited due to
        reaching their specified lifetime. Returns True if any workers were
        cleaned up.

        """
        if shutdown and not self._pool:
            raise WorkersJoined()

        cleaned, exitcodes = [], {}
        for i, process in enumerate(self._pool):
            if process.exitcode is not None:
                # worker exited
                process.join()
                cleaned.append(process.pid)
                exitcodes[process.pid] = process.exitcode
                self._queue.appendleft(process.controller)
                del self._pool[i]

        if cleaned:
            for pid in cleaned:
                self._putlock.release()
            return exitcodes.values()

        return []

    def _repopulate_pool(self, exitcodes):
        """Bring the number of pool processes up to the specified number,
        for use after reaping workers which have exited.

        """
        for i in xrange(self._processes - len(self._pool)):
            try:
                if exitcodes and exitcodes[i] != EX_OK:
                    self.restart_state.step()
            except IndexError:
                self.restart_state.step()
            self._create_worker_process()

    def _maintain_pool(self):
        """"Clean up any exited workers and start replacements for them."""
        self._repopulate_pool(self._join_exited_workers())

    def shrink(self, n=1):
        for i, process in enumerate(self._pool):
            self._processes -= 1
            self._putlock.shrink()
            process.terminate()
            if i == n - 1:
                return
        raise ValueError("Can't shrink pool. All processes busy!")

    def grow(self, n=1):
        for i in xrange(n):
            self._processes += 1
            if self._putlock:
                self._putlock.grow()

    def register(self, controller):
        self._queue.append(controller)
        self.grow()

    def start(self):
        for i in xrange(self._processes):
            self._create_worker_process()

    def stop(self):
        self.close()
        self.join()

    def close(self):
        self._putlock.clear()
        for process in self._pool:
            process.terminate()

    def join(self):
        for worker in self._pool:
            worker.join()


class PoolComponent(StartStopComponent):

    name = 'orchestrator.pool'
    requires = ('broker',)

    def create(self, parent):
        pool = parent.pool = Pool()
        return pool
