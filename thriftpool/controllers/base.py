# -*- coding: utf-8 -*-
"""Implements controllers.

This file was copied and adapted from celery.

:copyright: (c) 2009 - 2012 by Ask Solem.
:license: BSD, see LICENSE for more details.

"""
from __future__ import absolute_import

import uuid
from logging import getLogger

from thriftworker.utils.imports import qualname
from thriftworker.utils.finalize import Finalize
from thriftworker.utils.decorators import cached_property

from thriftpool.components.base import Namespace
from thriftpool.exceptions import SystemTerminate
from thriftpool.utils.mixin import LogsMixin
from thriftpool.utils.signals import Signals

__all__ = ['Controller']

logger = getLogger(__name__)


class Controller(LogsMixin):

    app = None

    wait_for_shutdown = True
    register_signals = True
    ignore_interrupt = False

    RUNNING = 0x1
    CLOSED = 0x2
    TERMINATED = 0x3

    Namespace = Namespace

    def __init__(self):
        self._starting = []
        self._running = 0
        self._state = None
        self._finalize = Finalize(self, self.stop, exitpriority=1)
        self.ident = uuid.uuid4()
        self.on_before_init()
        self.components = []
        self.namespace = self.Namespace(app=self.app).apply(self)

    @cached_property
    def _signals(self):
        return Signals()

    def register_signal_handler(self):
        self._debug('Register signal handlers')
        if not self.ignore_interrupt:
            self._signals['SIGINT'] = lambda signum, frame: self.stop()
        else:
            self._signals['SIGINT'] = lambda signum, frame: None
        self._signals['SIGTERM'] = lambda signum, frame: self.stop()
        self._signals['SIGQUIT'] = lambda signum, frame: self.terminate()

    def on_before_init(self):
        self.app.loader.on_before_init(self)
        self.app.finalize()

    def on_start(self):
        self.app.loader.on_start()

    def after_start(self):
        self.app.loader.after_start()

    def on_shutdown(self):
        self.app.loader.on_shutdown()

    def start(self):
        self._state = self.RUNNING

        if self.register_signals:
            self.register_signal_handler()

        self.on_start()

        try:
            for component in self.components:
                self._debug('Starting %s...', qualname(component))
                if component is not None:
                    self._starting.append(component)
                    component.start()
                self._running += 1
                self._debug('%s OK!', qualname(component))
        except SystemTerminate as exc:
            self._debug('Terminating server: %r', exc, exc_info=True)
            self.terminate()
        except Exception as exc:
            self._error('Unrecoverable error: %r', exc, exc_info=True)
            self.terminate()
        except (KeyboardInterrupt, SystemExit):
            self._debug('Terminating from keyboard')
            self.stop()
        finally:
            self._starting = []

        self._info('Controller %r started!', self)
        self.after_start()
        self._signals.wait()
        self._info('Controller %r stopped!', self)

    def _shutdown(self, warm=True):
        what = 'Stopping' if warm else 'Terminating'

        if self._state in (self.CLOSED, self.TERMINATED):
            return

        try:
            if not self.is_running or \
                    self._running != len(self.components):
                # Call abort on starting components.
                for component in self._starting[:]:
                    self._debug('Aborting %s...', qualname(component))
                    if hasattr(component, 'abort'):
                        component.abort()
                # Not fully started, can safely exit.
                self._state = self.TERMINATED
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
            self._debug('Whole controller stopped!')
            self._state = self.TERMINATED
        except Exception as exc:
            self._error('Unrecoverable error: %r', exc, exc_info=True)
        finally:
            self._signals.set()

    @property
    def is_running(self):
        return self._state == self.RUNNING

    def stop(self):
        """Graceful shutdown of the worker server."""
        self._debug('Try to stop controller!')
        self._shutdown(warm=True)

    def terminate(self):
        """Not so graceful shutdown of the worker server."""
        self._debug('Try to terminate controller!')
        self._shutdown(warm=False)
