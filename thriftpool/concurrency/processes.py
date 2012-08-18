from __future__ import absolute_import

from collections import deque
from logging import getLogger
import itertools
import time

from billiard import Process as _Process
from billiard.common import restart_state
from billiard.pool import LaxBoundedSemaphore, EX_OK, WorkersJoined
from billiard.exceptions import RestartFreqExceeded
from zope.interface import implementer

from thriftpool.concurrency.base import IPoolController
from thriftpool.utils.other import setproctitle
from thriftpool.utils.threads import LoopThread
from thriftpool.utils.signals import signals

__all__ = ['ProcessPoolController']

logger = getLogger(__name__)


class Process(_Process):
    """Process that will execute given controller."""

    def __init__(self, controller, num=0):
        self.controller = controller
        super(Process, self).__init__(
            name="{0}-{1}".format(type(self.controller).__name__, num))

    def run(self):
        # Change process title.
        setproctitle('[{0.name}]'.format(self))

        # Register signals.
        signals['SIGINT'] = lambda signum, frame: self.controller.stop()
        signals['SIGTERM'] = lambda signum, frame: self.controller.stop()
        signals['SIGQUIT'] = lambda signum, frame: self.controller.terminate()

        # Start controller.
        self.controller.start()


class Supervisor(LoopThread):

    def __init__(self, pool):
        self.pool = pool
        super(Supervisor, self).__init__()

    def on_start(self):
        pool = self.pool
        try:
            # Do a burst at startup to verify that we can start
            # our pool processes, and in that time we lower
            # the max restart frequency.
            prev_state = pool.restart_state
            pool.restart_state = restart_state(2, 1)
            for _ in xrange(10):
                pool._maintain_pool()
                time.sleep(0.1)

            # Restore previous state.
            pool.restart_state = prev_state

        except RestartFreqExceeded:
            pool.close()
            pool.join()
            raise

    def loop(self):
        pool = self.pool
        try:
            # Keep maintaining workers.
            pool._maintain_pool()
            time.sleep(0.8)

        except RestartFreqExceeded:
            pool.close()
            pool.join()
            raise


@implementer(IPoolController)
class ProcessPoolController(object):
    """Spawn and maintain worker pool. Based on :class:`billiard.pool.Pool`."""

    Process = Process
    Supervisor = Supervisor

    def __init__(self):
        self._pool = []
        self._queue = deque()
        self._processes = 0
        self._next_number = itertools.count()
        self.restart_state = restart_state(5, 1)
        self._putlock = LaxBoundedSemaphore(self._processes)
        self._supervisor = self.Supervisor(self)

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

    def start(self):
        self._supervisor.start()
        for i in xrange(self._processes):
            self._create_worker_process()

    def close(self):
        self._putlock.clear()
        for process in self._pool:
            process.terminate()

    def join(self):
        for worker in self._pool:
            worker.join()

    def stop(self):
        self._supervisor.stop()
        self.close()
        self.join()

        # Prevent loops.
        self._supervisor = None

    def register(self, controller):
        self._queue.append(controller)
        self.grow()
