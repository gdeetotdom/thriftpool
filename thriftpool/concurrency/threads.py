from __future__ import absolute_import

from zope.interface import implementer

from thriftpool.concurrency.base import IPoolController
from thriftpool.utils.threads import DaemonThread


class Thread(DaemonThread):
    """Container for controller."""

    def __init__(self, controller, num=0):
        self.controller = controller
        super(Thread, self).__init__(
            name="{0}-{1}".format(type(self.controller).__name__, num))

    def body(self):
        self.controller.start()

    def stop(self):
        self.controller.stop()
        super(Thread, self).stop()


@implementer(IPoolController)
class ThreadPoolController(object):
    """Spawn and maintain worker pool. Based on :class:`billiard.pool.Pool`."""

    Thread = Thread

    def __init__(self):
        self._pool = []
        self._started = False

    def start(self):
        self._started = True
        for thread in self._pool:
            thread.start()

    def stop(self):
        self._started = False
        while self._pool:
            thread = self._pool.pop()
            thread.stop()

    def register(self, controller):
        t = self.Thread(controller)
        self._pool.append(t)
        if self._started:
            t.start()
