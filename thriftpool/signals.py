"""Specify signals sent when specific events happens."""
from thriftpool.utils.dispatch import Signal


#: Called before handler will be guarded. Handler may return decorator.
handler_method_guarded = Signal(providing_args=['fn'])


#: Listener was started.
listener_started = Signal(providing_args=['listener', 'app'])


#: Listener was stopped.
listener_stopped = Signal(providing_args=['listener', 'app'])


#: Called before loggers are configured.
setup_logging = Signal(providing_args=['root', 'logfile'])
