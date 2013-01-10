from __future__ import absolute_import

from functools import partial

from thriftworker.utils.loop import in_loop

from thriftpool.app import current_app


class Proxy(object):
    """Proxy object that execute functions on other side."""

    def __init__(self, producer):
        self.__producer = producer

    def __getattr__(self, name):
        """Create inner function that should enqueue remote procedure call."""
        producer = self.__producer

        def execute_callback(waiter, obj):
            if isinstance(obj, Exception):
                waiter.throw(obj)
            else:
                waiter.switch(obj)

        def inner_function(*args, **kwargs):
            waiter = current_app.hub.Waiter()
            producer.apply(name, callback=partial(execute_callback, waiter),
                           args=args, kwargs=kwargs)
            return waiter.get()

        inner_function.__name__ = name
        setattr(self, name, inner_function)
        return inner_function


class Client(object):
    """Client to """

    Proxy = Proxy

    def __init__(self, producer):
        self.__proxy = self.Proxy(producer)

    @in_loop
    def spawn(self, run, **kwargs):
        """Spawn given function in separate greenlet. Keyword
        argument `proxy` will be passed to provided function.

        """
        assert callable(run), 'given object not callable'
        kwargs.setdefault('proxy', self.__proxy)
        return current_app.hub.spawn(run, **kwargs)
