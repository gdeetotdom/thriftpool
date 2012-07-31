from __future__ import absolute_import
from billiard import Process
from billiard.common import restart_state
from billiard.pool import LaxBoundedSemaphore, EX_OK, WorkersJoined
from logging import getLogger
from threading import Event
from thriftpool.components.base import StartStopComponent
from thriftpool.utils.logs import LogsMixin
from thriftpool.utils.signals import signals
import uuid

logger = getLogger(__name__)


class PoolComponent(StartStopComponent):

    name = 'orchestrator.pool'
    requires = ('broker',)

    def create(self, parent):
        pool = parent.pool = Pool(parent.app, parent)
        return pool


class Worker(LogsMixin):

    def __init__(self, app, container):
        self._shutdown_complete = Event()
        self.ident = uuid.uuid4().hex
        self.app = app
        self.container = container
        self.remote_worker = self.app.RemoteWorker(self.ident, self.container)

    def register_signal_handler(self):
        signals['SIGINT'] = lambda signum, frame: self.stop()
        signals['SIGTERM'] = lambda signum, frame: self.stop()

    def run(self):
        self._debug('Starting worker "%s".', self.ident)

        # wait for termination signal
        self.register_signal_handler()

        # start remote worker and container
        self.container.on_start()
        self.remote_worker.start()

        # wait for shutdown event
        while not self._shutdown_complete.is_set():
            self._shutdown_complete.wait(1e100)

        # stop remote worker and wait until it will exit
        self.remote_worker.stop()
        self.container.on_stop()

        # stop hub and wait until it will exit
        self.app.hub.stop()

    def stop(self):
        self._debug('Stopping worker "%s".', self.ident)
        self._shutdown_complete.set()


class Pool(object):

    def __init__(self, app, controller):
        self.app = app
        self.controller = controller
        self._pool = []
        self._workers = []
        self._processes = 0
        self.restart_state = restart_state(10, 1)
        self._putlock = LaxBoundedSemaphore(self._processes)

    def _create_worker_process(self):
        p = Process(target=self._workers.pop(0).run)
        self._pool.append(p)
        p.daemon = True
        p.start()

    def _join_exited_workers(self, shutdown=False):
        """Cleanup after any worker processes which have exited due to
        reaching their specified lifetime. Returns True if any workers were
        cleaned up.

        """
        if shutdown and not len(self._pool):
            raise WorkersJoined()

        cleaned, exitcodes = [], {}
        for i in reversed(range(len(self._pool))):
            worker = self._pool[i]
            if worker.exitcode is not None:
                # worker exited
                worker.join()
                cleaned.append(worker.pid)
                exitcodes[worker.pid] = worker.exitcode
                del self._pool[i]

        if cleaned:
            for worker in cleaned:
                self._putlock.release()
            return exitcodes.values()

        return []

    def _repopulate_pool(self, exitcodes):
        """Bring the number of pool processes up to the specified number,
        for use after reaping workers which have exited.

        """
        for i in range(self._processes - len(self._pool)):
            if self.controller._state != self.controller.RUNNING:
                return
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
        for i, worker in enumerate(self._pool):
            self._processes -= 1
            self._putlock.shrink()
            worker.terminate()
            if i == n - 1:
                return
        raise ValueError("Can't shrink pool. All processes busy!")

    def grow(self, n=1):
        for i in xrange(n):
            self._processes += 1
            if self._putlock:
                self._putlock.grow()

    def create(self, container):
        worker = Worker(self.app, container)
        self._workers.append(worker)
        self.grow()
        return worker.ident

    def start(self):
        for i in xrange(self._processes):
            self._create_worker_process()

    def stop(self):
        self.close()
        self.join()

    def close(self):
        self._putlock.clear()
        for worker in self._pool:
            worker.terminate()

    def join(self):
        for worker in self._pool:
            worker.join()
