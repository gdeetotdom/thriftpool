from __future__ import absolute_import

from functools import partial

from thriftworker.utils.loop import in_loop


class Proxy(object):
    """Proxy object that execute functions on other side."""

    def __init__(self, app, producer):
        self._app = app
        self._producer = producer

    def __getattr__(self, name):
        """Create inner function that should enqueue remote procedure call."""
        producer = self._producer
        app = self._app

        def execute_callback(waiter, obj):
            if isinstance(obj, Exception):
                waiter.throw(obj)
            else:
                waiter.switch(obj)

        def inner_function(*args, **kwargs):
            waiter = app.hub.Waiter()
            producer.apply(name, callback=partial(execute_callback, waiter),
                           args=args, kwargs=kwargs)
            return waiter.get()

        inner_function.__name__ = name
        setattr(self, name, inner_function)
        return inner_function


class Client(object):
    """Provide simple interface to pass commands to slaves."""

    Proxy = Proxy

    def __init__(self, app, producer):
        self.app = app
        self.proxy = self.Proxy(self.app, producer)

    @in_loop
    def spawn(self, run, **kwargs):
        """Spawn given function in separate greenlet. Keyword
        argument `proxy` will be passed to provided function.

        """
        assert callable(run), 'given object not callable'
        kwargs['proxy'] = self.proxy
        return self.app.hub.spawn(run, **kwargs)
