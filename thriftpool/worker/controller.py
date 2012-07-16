from __future__ import absolute_import
from functools import partial
from logging import getLogger
from threading import Event
from thriftpool.exceptions import SystemTerminate
from thriftpool.utils.imports import qualname
from thriftpool.utils.signals import signals
from thriftpool.worker.abstract import Namespace as BaseNamespace

__all__ = ['Controller']

logger = getLogger(__name__)

RUNNING = 0x1
CLOSED = 0x2
TERMINATED = 0x3


class Namespace(BaseNamespace):
    """This is the boot-step namespace of the :class:`Controller`."""
    name = 'worker'

    def modules(self):
        return ['thriftpool.worker.broker',
                'thriftpool.worker.pool']


class Controller(object):

    app = None

    RUNNING = RUNNING
    CLOSED = CLOSED
    TERMINATED = TERMINATED

    def __init__(self):
        self._running = 0
        self._state = None
        self._shutdown_complete = Event()
        self.components = []
        self.namespace = Namespace(app=self.app).apply(self)

    def _signal_handler(self, signum, frame, callback):
        callback()

    def register_signal_handler(self):
        logger.debug('Register signal handlers')
        signals['SIGINT'] = partial(self._signal_handler, callback=self.stop)
        signals['SIGTERM'] = partial(self._signal_handler, callback=self.stop)
        signals['SIGQUIT'] = partial(self._signal_handler, callback=self.terminate)

    def start(self):
        self._state = self.RUNNING

        self.register_signal_handler()

        try:
            for component in self.components:
                logger.debug('Starting %s...', qualname(component))
                if component is not None:
                    component.start()
                self._running += 1
                logger.debug('%s OK!', qualname(component))
        except SystemTerminate as exc:
            logger.debug('Terminating server: %r', exc, exc_info=True)
            self.terminate()
        except Exception as exc:
            logger.error('Unrecoverable error: %r', exc, exc_info=True)
            self.stop()
        except (KeyboardInterrupt, SystemExit):
            logger.debug('Terminating from keyboard')
            self.stop()

        # we can't simply execute Event.wait because signal processing will
        # not work in this case
        while not self._shutdown_complete.is_set():
            self._shutdown_complete.wait(1e100)

    def _shutdown(self, warm=True):
        what = 'Stopping' if warm else 'Terminating'

        if self._state in (self.CLOSED, self.TERMINATED):
            return

        if self._state != self.RUNNING or self._running != len(self.components):
            # Not fully started, can safely exit.
            self._state = self.TERMINATED
            self._shutdown_complete.set()
            return

        self._state = self.CLOSED

        for component in reversed(self.components):
            logger.debug('%s %s...', what, qualname(component))
            if component:
                stop = component.stop
                if not warm:
                    stop = getattr(component, 'terminate', None) or stop
                stop()

        self._state = self.TERMINATED
        self._shutdown_complete.set()

    def stop(self):
        """Graceful shutdown of the worker server."""
        logger.info('Stop server!')
        self._shutdown(warm=True)

    def terminate(self):
        """Not so graceful shutdown of the worker server."""
        logger.info('Terminate server!')
        self._shutdown(warm=False)
