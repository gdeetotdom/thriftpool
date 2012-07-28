from __future__ import absolute_import
from billiard import Process
from billiard.common import restart_state
from billiard.pool import LaxBoundedSemaphore, EX_OK, WorkersJoined
from logging import getLogger
from threading import Event
from thriftpool.components.base import StartStopComponent
from thriftpool.utils.functional import cached_property
from thriftpool.utils.signals import signals
import uuid
from thriftpool.utils.logs import LogsMixin

logger = getLogger(__name__)


class PoolComponent(StartStopComponent):

    name = 'orchestrator.pool'
    requires = ('broker',)

    def create(self, parent):
        pool = parent.pool = Pool(parent.app, parent)
        return pool


class WorkerController(LogsMixin):

    def __init__(self, app):
        self._shutdown_complete = Event()
        self.app = app
        self.ident = uuid.uuid4().hex
        self.remote_worker = self.app.RemoteWorker(self.ident, self)

    def run(self):
        self._debug('Starting worker "%s".', self.ident)

        # start remote worker
        self.remote_worker.start()

        # wait for shutdown event
        while not self._shutdown_complete.is_set():
            self._shutdown_complete.wait(1e100)

        # stop remote worker
        self.remote_worker.stop()

    def stop(self):
        self._debug('Stopping worker "%s".', self.ident)
        self._shutdown_complete.set()

    def ping(self):
        return 'pong'


class Worker(Process):

    def __init__(self, app):
        self.app = app
        super(Worker, self).__init__()

    @cached_property
    def controller(self):
        return WorkerController(self.app)

    def register_signal_handler(self):
        signals['SIGTERM'] = lambda signum, frame: self.controller.stop()

    def run(self):
        # wait for termination signal
        self.register_signal_handler()

        # start controller
        self.controller.run()

        # stop hub and wait until it will exit
        self.app.hub.stop()
        self.app.hub.wait_shutdown()


class Pool(object):

    Worker = Worker

    def __init__(self, app, controller, processes=None):
        self.app = app
        self.controller = controller
        self._pool = []
        self._processes = processes or 1
        self.restart_state = restart_state(self._processes * 4, 1)
        self._putlock = LaxBoundedSemaphore(self._processes)

    def _create_worker_process(self):
        w = self.Worker(self.app)
        self._pool.append(w)
        w.daemon = True
        w.start()
        return w

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
