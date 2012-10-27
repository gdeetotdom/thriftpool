# -*- coding: utf-8 -*-
"""Implements controllers.

This file was copied and adapted from celery.

:copyright: (c) 2009 - 2012 by Ask Solem.
:license: BSD, see LICENSE for more details.

"""
from __future__ import absolute_import

from logging import getLogger
from threading import Event

from thriftpool.components.base import Namespace
from thriftpool.exceptions import SystemTerminate
from thriftpool.utils.finalize import Finalize
from thriftpool.utils.mixin import LogsMixin
from thriftpool.utils.signals import signals
from thriftpool.utils.imports import qualname

__all__ = ['Controller']

logger = getLogger(__name__)


class Controller(LogsMixin):

    app = None

    wait_for_shutdown = True
    register_signals = True

    RUNNING = 0x1
    CLOSED = 0x2
    TERMINATED = 0x3

    Namespace = Namespace

    def __init__(self):
        self._running = 0
        self._state = None
        self._shutdown_complete = Event()
        self._finalize = Finalize(self, self.stop, exitpriority=1)
        self.on_before_init()
        self.components = []
        self.namespace = self.Namespace(app=self.app).apply(self)

    def register_signal_handler(self):
        self._debug('Register signal handlers')
        signals['SIGINT'] = lambda signum, frame: self.stop()
        signals['SIGTERM'] = lambda signum, frame: self.stop()
        signals['SIGQUIT'] = lambda signum, frame: self.terminate()

    def on_before_init(self):
        pass

    def on_start(self):
        pass

    def after_start(self):
        pass

    def on_shutdown(self):
        pass

    def start(self):
        self._state = self.RUNNING

        if self.register_signals:
            self.register_signal_handler()

        self.on_start()

        try:
            for component in self.components:
                self._debug('Starting %s...', qualname(component))
                if component is not None:
                    component.start()
                self._running += 1
                self._debug('%s OK!', qualname(component))
        except SystemTerminate as exc:
            self._debug('Terminating server: %r', exc, exc_info=True)
            self.terminate()
        except Exception as exc:
            self._error('Unrecoverable error: %r', exc, exc_info=True)
            self.stop()
        except (KeyboardInterrupt, SystemExit):
            self._debug('Terminating from keyboard')
            self.stop()

        self._debug('Controller started!')

        self.after_start()

        # we can't simply execute Event.wait because signal processing will
        # not work in this case
        while self.wait_for_shutdown and not self._shutdown_complete.is_set():
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
            self._debug('%s %s...', what, qualname(component))
            if component:
                stop = component.stop
                if not warm:
                    stop = getattr(component, 'terminate', None) or stop
                stop()

        self.on_shutdown()

        self._debug('Controller stopped!')

        self._state = self.TERMINATED
        self._shutdown_complete.set()

    def stop(self):
        """Graceful shutdown of the worker server."""
        self._debug('Try to stop controller!')
        self._shutdown(warm=True)

    def terminate(self):
        """Not so graceful shutdown of the worker server."""
        self._debug('Try to terminate controller!')
        self._shutdown(warm=False)
