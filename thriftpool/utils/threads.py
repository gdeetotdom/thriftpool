from __future__ import absolute_import
from threading import Thread, Event
import os
import sys
import traceback

__all__ = ['SimpleDaemonThread']


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
        except Exception as exc:
            try:
                self.on_crash('{0!r} crashed: {1!r}', self.name, exc)
            finally:
                os._exit(1)  # exiting by normal means won't work
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

    def on_crash(self, msg, *fmt):
        sys.stderr.write(msg.format(*fmt) + '\n')
        exc_info = sys.exc_info()
        try:
            traceback.print_exception(exc_info[0], exc_info[1], exc_info[2],
                                      None, sys.stderr)
        finally:
            del(exc_info)


class SimpleDaemonThread(DaemonThread):

    def __init__(self, target, name=None, **kwargs):
        self.target = target
        super(SimpleDaemonThread, self).__init__(name, **kwargs)

    def body(self):
        self.target()
