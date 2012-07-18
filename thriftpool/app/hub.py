# -*- coding: utf-8 -*-
"""Implements event loop.

This file was copied and adapted from gevent.

"""
from functools import partial
from greenlet import greenlet, getcurrent, GreenletExit
from thriftpool.utils.exceptions import set_exc_info
from thriftpool.utils.functional import cached_property
from thriftpool.utils.mixin import SubclassMixin
import pyev
import sys

__all__ = ['Hub']


class Hub(SubclassMixin):
    """Class that run event loop."""

    app = None

    def __init__(self):
        self.loop = pyev.Loop(debug=True)
        self._async_stop = self.loop.async(self._shutdown)
        self._async_stop.start()
        super(Hub, self).__init__()

    @cached_property
    def _greenlet(self):
        return greenlet(run=self.run)

    @cached_property
    def Greenlet(self):
        return self.subclass_with_self(Greenlet, attribute='hub')

    @cached_property
    def Waiter(self):
        return self.subclass_with_self(Waiter, attribute='hub')

    def wait(self, watcher):
        """Wait until watcher will be executed."""
        waiter = self.Waiter()
        unique = object()
        watcher.start(waiter.switch, unique)
        try:
            result = waiter.get()
            assert result is unique, 'Invalid switch into %s: %r (expected %r)' % (getcurrent(), result, unique)
        finally:
            watcher.stop()

    @cached_property
    def io(self):
        return self.subclass_with_self(IOWatcher, attribute='hub')

    @cached_property
    def async(self):
        return self.subclass_with_self(AsyncWatcher, attribute='hub')

    def start(self):
        self._greenlet.switch()

    def run(self):
        self.loop.start()

    def _shutdown(self, watcher, revents):
        self.loop.stop()

    def stop(self):
        # we should run shutdown method in same thread as loop's thread
        self._async_stop.send()

    def switch(self):
        """Return to main loop. Save exception information before."""
        exc_type, exc_value = sys.exc_info()[:2]
        try:
            switch_out = getattr(getcurrent(), 'switch_out', None)
            if switch_out is not None:
                switch_out()
            sys.exc_clear()
            return self._greenlet.switch()
        finally:
            set_exc_info(exc_type, exc_value)

    def switch_out(self):
        """Method to prevent loops."""
        raise RuntimeError('Impossible to call blocking function in the event loop callback')

    def run_in_loop(self, callback, *args, **kwargs):
        """Run given function in loop."""
        watcher = self.async()
        watcher.start(callback, *args, **kwargs)
        watcher.send()
        return watcher


class Waiter(object):
    """A low level communication utility for greenlets."""

    hub = None

    __slots__ = ['greenlet', 'value', '_exception']

    def __init__(self,):
        self.greenlet = None
        self.value = None
        self._exception = _NONE

    def clear(self):
        self.greenlet = None
        self.value = None
        self._exception = _NONE

    def __str__(self):
        if self._exception is _NONE:
            return '<%s greenlet=%s>' % (type(self).__name__, self.greenlet)
        elif self._exception is None:
            return '<%s greenlet=%s value=%r>' % (type(self).__name__,
                                                  self.greenlet,
                                                  self.value)
        else:
            return '<%s greenlet=%s exc_info=%r>' % (type(self).__name__,
                                                     self.greenlet,
                                                     self.exc_info)

    def ready(self):
        """Return true if and only if it holds a value or an exception"""
        return self._exception is not _NONE

    def successful(self):
        """Return true if and only if it is ready and holds a value"""
        return self._exception is None

    @property
    def exc_info(self):
        """Holds the exception info passed to :meth:`throw` if :meth:`throw`
        was called. Otherwise ``None``.

        """
        if self._exception is not _NONE:
            return self._exception

    def switch(self, value=None):
        """Switch to the greenlet if one's available. Otherwise store the
        value.

        """
        if self.greenlet is None:
            self.value = value
            self._exception = None
        else:
            assert getcurrent() is self.hub, "Can only use Waiter.switch" \
                " method from the Hub greenlet"
            self.greenlet.switch(value)

    def switch_args(self, *args):
        return self.switch(args)

    def throw(self, *throw_args):
        """Switch to the greenlet with the exception. If there's no greenlet," \
            " store the exception."""
        if self.greenlet is None:
            self._exception = throw_args
        else:
            assert getcurrent() is self.hub, "Can only use Waiter.switch" \
                " method from the Hub greenlet"
            self.greenlet.throw(*throw_args)

    def get(self):
        """If a value/an exception is stored, return/raise it. Otherwise until
        switch() or throw() is called.

        """
        if self._exception is not _NONE:
            if self._exception is None:
                return self.value
            else:
                getcurrent().throw(*self._exception)
        else:
            assert self.greenlet is None, 'This Waiter is already used by %r' \
                % (self.greenlet,)
            self.greenlet = getcurrent()
            try:
                return self.hub.switch()
            finally:
                self.greenlet = None


class BaseWatcher(object):
    """Base class for all watchers."""

    hub = None

    def __init__(self, *args, **kwargs):
        self.callback = None
        self.loop = self.hub.loop
        self.watcher = self.create(*args, callback=self.on_ready, **kwargs)

    def create(self, *args, **kwargs):
        raise NotImplementedError()

    def on_ready(self, watcher, revents):
        """Called when event fired."""
        self.callback()

    def start(self, callback, *args, **kwargs):
        """Run watcher """
        self.callback = partial(callback, *args, **kwargs)
        self.watcher.start()

    def stop(self):
        """Closes and unset watcher."""
        self.watcher.stop()
        # prevent loops
        self.callback = self.watcher = None


class IOWatcher(BaseWatcher):
    """Wait for events on file descriptor."""

    def create(self, fd, events, callback):
        return self.loop.io(fd, events, callback)


class AsyncWatcher(BaseWatcher):
    """Wait for external events."""

    def create(self, callback):
        return self.loop.async(callback, pyev.EV_MAXPRI)

    def send(self):
        self.watcher.send()


class Greenlet(greenlet):
    """A light-weight cooperatively-scheduled execution unit."""

    hub = None

    def __init__(self, run=None, *args, **kwargs):
        greenlet.__init__(self, parent=self.hub._greenlet)
        if run is not None:
            self._run = run
        self.args = args
        self.kwargs = kwargs
        self._start_watcher = None

    def start(self):
        """Schedule the greenlet to run in this loop iteration"""
        if self._start_watcher is None:
            self._start_watcher = self.hub.async()
            self._start_watcher.start(self.switch)
            self._start_watcher.send()

    def run(self):
        try:
            if self._start_watcher is not None:
                self._start_watcher.stop()
            self._run(*self.args, **self.kwargs)
        finally:
            self.__dict__.pop('_run', None)
            self.__dict__.pop('args', None)
            self.__dict__.pop('kwargs', None)

    def kill(self, exception=GreenletExit):
        """Raise the exception in the greenlet."""
        if not self.dead:
            self.hub.run_in_loop(lambda: self.throw(exception))


class _NONE(object):
    "A special thingy you must never pass to any of API"

    __slots__ = []

    def __repr__(self):
        return '<_NONE>'

_NONE = _NONE()
