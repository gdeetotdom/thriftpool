"""Specify signals sent when specific events happens."""
from thriftpool.utils.dispatch import Signal

__all__ = ['handler_method_guarded']


#: Called before handler will be guarded. Handler may return decorator.
handler_method_guarded = Signal(providing_args=['fn'])
