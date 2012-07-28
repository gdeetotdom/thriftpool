from __future__ import absolute_import
from billiard.common import restart_state
from billiard.exceptions import RestartFreqExceeded
from thriftpool.components.base import StartStopComponent
from thriftpool.utils.threads import DaemonThread
import time


class SupervisorComponent(StartStopComponent):

    name = 'orchestrator.supervisor'
    requires = ('pool',)

    def create(self, parent):
        supervisor = parent.supervisor = Supervisor(parent.pool, parent)
        return supervisor


class Supervisor(DaemonThread):

    def __init__(self, pool, controller):
        self.pool = pool
        self.controller = controller
        super(Supervisor, self).__init__()

    def body(self):
        pool = self.pool
        controller = self.controller

        time.sleep(0.8)

        try:
            # do a burst at startup to verify that we can start
            # our pool processes, and in that time we lower
            # the max restart frequency.
            prev_state = pool.restart_state
            pool.restart_state = restart_state(pool._processes * 2, 1)
            for _ in xrange(10):
                if controller._state == controller.RUNNING:
                    pool._maintain_pool()
                    time.sleep(0.1)

            # Keep maintaining workers until the cache gets drained, unless
            # the pool is terminated
            pool.restart_state = prev_state
            while controller._state == controller.RUNNING:
                pool._maintain_pool()
                time.sleep(0.8)

        except RestartFreqExceeded:
            pool.close()
            pool.join()
            raise
