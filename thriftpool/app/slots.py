"""Implement service repository."""
from collections import namedtuple
from thriftpool.handlers import ProcessorMixin, HandlerMeta
from thriftpool.utils.functional import cached_property
from thriftpool.utils.imports import symbol_by_name

__all__ = ['Repository']


class Listener(namedtuple('Listener', 'host port backlog')):
    """Specify which port we should listen."""


class ThriftService(namedtuple('ThriftService', 'processor_cls handler_cls')):
    """Describe service information."""

    @cached_property
    def Handler(self):
        """Recreate handler class."""
        cls = symbol_by_name(self.handler_cls)
        return HandlerMeta(cls.__name__, cls.__bases__, dict(cls.__dict__))

    @cached_property
    def handler(self):
        """Create handler instance."""
        return self.Handler()

    @cached_property
    def Processor(self):
        """Create safe processor."""
        cls = symbol_by_name(self.processor_cls)
        return type(cls.__name__, (ProcessorMixin, cls), dict())

    @cached_property
    def processor(self):
        """Create processor instance."""
        return self.Processor(self.handler)


class Slot(namedtuple('Slot', 'name listener service')):
    """Combine service and listener together."""


class Repository(set):
    """Store existed slots."""

    def register(self, name, processor_cls, handler_cls, **opts):
        listener = Listener(host=opts.get('host', '0.0.0.0'),
                            port=opts.get('port'),
                            backlog=opts.get('backlog'))
        service = ThriftService(processor_cls=processor_cls,
                                handler_cls=handler_cls)
        self.add(Slot(name, listener, service))
