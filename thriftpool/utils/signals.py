from __future__ import absolute_import

import signal as _signal

import pyuv

from six import iteritems, string_types

__all__ = ['signals']


class Signals(object):
    """Convenience interface to :mod:`signals`.

    **Examples**:

    .. code-block:: python

        >>> from . import signals
        >>> signals = Signals()

        >>> signals['INT'] = my_handler

        >>> signals['INT']
        my_handler

        >>> signals.supported('INT')
        True

        >>> signals.signum('INT')
        2

    """

    def __init__(self):
        self._loop = pyuv.Loop.default_loop()
        self._signal_handlers = []
        self._registered_signals = {}
        self._guard = None
        self._flag = False

    def supported(self, signal_name):
        """Returns true value if ``signal_name`` exists on this platform."""
        try:
            return self.signum(signal_name)
        except AttributeError:
            pass

    def signum(self, signal_name):
        """Get signal number from signal name."""
        if isinstance(signal_name, int):
            return signal_name
        if not isinstance(signal_name, string_types) \
                or not signal_name.isupper():
            raise TypeError('signal name must be uppercase string.')
        if not signal_name.startswith('SIG'):
            signal_name = 'SIG' + signal_name
        return getattr(_signal, signal_name)

    def __getitem__(self, signal_name):
        return self._registered_signals[self.signum(signal_name)]

    def __setitem__(self, signal_name, handler):
        """Install signal handler."""
        self._registered_signals[self.signum(signal_name)] = handler

    def update(self, _d_=None, **sigmap):
        """Set signal handlers from a mapping."""
        for signal_name, handler in iteritems(dict(_d_ or {}, **sigmap)):
            self[signal_name] = handler

    def _on_signal(self, handle, signum):
        try:
            callback = self._registered_signals[signum]
        except KeyError:
            pass
        else:
            callback(signum, self)

    def _start_signal(self, callback, signum):
        h = pyuv.Signal(self._loop)
        h.start(callback, signum)
        h.unref()
        self._signal_handlers.append(h)

    def start(self):
        # quit signals handling
        for signum in self._registered_signals:
            self._start_signal(self._on_signal, signum)

    def stop(self):
        signal_handlers, self._signal_handlers = self._signal_handlers, []
        for handle in signal_handlers:
            try:
                handle.stop()
            except pyuv.error.HandleError:
                pass

    def wait(self):
        """Wait for signal or until set call."""
        if self._flag:
            return
        self.start()
        self._guard = pyuv.Async(self._loop, lambda h: None)
        try:
            self._loop.run()
        finally:
            self.stop()

    def set(self):
        """Exit from loop."""
        self._flag = True
        if self._guard is None:
            return
        self._guard.close()
