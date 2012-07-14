from __future__ import absolute_import
from threading import Thread, Event

__all__ = ['DaemonThread']


class DaemonThread(Thread):

    def __init__(self, name=None, **kwargs):
        super(DaemonThread, self).__init__()
        self._is_stopped = Event()
        self.daemon = True
        self.name = name or self.__class__.__name__

    def body(self):
        raise NotImplementedError('subclass responsibility')

    def run(self):
        try:
            self.body()
        finally:
            self._set_stopped()

    def _set_stopped(self):
        try:
            self._is_stopped.set()
        except TypeError:  # pragma: no cover
            # we lost the race at interpreter shutdown,
            # so gc collected built-in modules.
            pass

    def stop(self):
        """Graceful shutdown."""
        self._is_stopped.wait()
        if self.is_alive():
            self.join(1e100)
