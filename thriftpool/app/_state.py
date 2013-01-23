"""Handle global package state."""
from __future__ import absolute_import

from thriftworker.utils.proxy import Proxy

default_cls = None
default_app = None


def as_default_cls(cls):
    global default_cls
    default_cls = cls
    return cls


def get_default_cls():
    global default_cls
    if default_cls is None:
        from thriftpool.app.base import ThriftPool
        return ThriftPool
    return default_cls


def set_current_app(app):
    global default_app
    default_app = app


def get_current_app():
    global default_app
    if default_app is None:
        # creates the default app, but we want to defer that.
        cls = get_default_cls()
        set_current_app(cls())
    return default_app


current_app = Proxy(get_current_app)
