"""Implement service repository."""
from collections import namedtuple
from thriftpool.utils.functional import cached_property
from thriftpool.utils.imports import symbol_by_name
from thriftpool.utils.other import mk_temp_path

__all__ = ['Repository']


class Listener(namedtuple('Listener', 'host port backlog')):
    """Specify which port we should listen."""


class ThriftService(namedtuple('ThriftService', 'processor_cls handler_cls')):
    """Describe service information."""

    @cached_property
    def Processor(self):
        return symbol_by_name(self.processor_cls)

    @cached_property
    def Handler(self):
        return symbol_by_name(self.handler_cls)

    @cached_property
    def processor(self):
        return self.Processor(self.handler)

    @cached_property
    def handler(self):
        return self.Handler()


class Slot(namedtuple('Slot', 'name listener service backend')):
    """Combine service and listener together."""


class Repository(set):
    """Store existed slots."""

    def register(self, name, processor_cls, handler_cls, **opts):
        listener = Listener(host=opts.get('host', '0.0.0.0'),
                            port=opts.get('port'),
                            backlog=opts.get('backlog', 1024))
        service = ThriftService(processor_cls=processor_cls,
                                handler_cls=handler_cls)
        backend = 'ipc://{0}'.format(mk_temp_path(prefix='slot'))
        self.add(Slot(name, listener, service, backend))

