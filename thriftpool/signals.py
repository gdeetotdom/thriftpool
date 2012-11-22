"""Specify signals sent when specific events happens."""
from __future__ import absolute_import

from thriftpool.utils.dispatch import Signal


#: Called before handler will be guarded. Handler may return decorator.
handler_method_guarded = Signal(providing_args=['fn'])


#: Listener was started.
listener_started = Signal(providing_args=['listener', 'slot', 'app'])


#: All listener was started.
listeners_started = Signal(providing_args=['app'])


#: Listener was stopped.
listener_stopped = Signal(providing_args=['listener', 'slot', 'app'])


#: All listeners stopped.
listeners_stopped = Signal(providing_args=['app'])


#: Called before loggers are configured.
setup_logging = Signal(providing_args=['root', 'logfile', 'loglevel'])


#: Called after loggers are configured.
after_logging_setup = Signal(providing_args=['root', 'logfile', 'loglevel'])


#: Called on application start.
app_start = Signal(providing_args=['app'])


#: Called after application start.
after_app_start = Signal(providing_args=['app'])


#: Called after application stopped.
app_shutdown = Signal(providing_args=['app'])


#: Collect file descriptors that must not be closed.
collect_excluded_fds = Signal(providing_args=[])
