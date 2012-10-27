"""Implement service repository."""
from __future__ import absolute_import

from collections import namedtuple

from thriftworker.utils.decorators import cached_property

from thriftpool.request.handler import WrappedHandlerMeta
from thriftpool.request.processor import ProcessorMixin
from thriftpool.exceptions import RegistrationError
from thriftpool.utils.imports import symbol_by_name

__all__ = ['Repository']


class Listener(namedtuple('Listener', 'host port backlog')):
    """Specify which port we should listen."""


class ThriftService(namedtuple('ThriftService', 'service_name processor_cls handler_cls')):
    """Describe service information."""

    @cached_property
    def Handler(self):
        """Recreate handler class."""
        return symbol_by_name(self.handler_cls)

    @cached_property
    def handler(self):
        """Create handler instance."""
        return self.Handler()

    @cached_property
    def WrappedHandler(self):
        """Create wrapped handler instance."""
        Handler = self.Handler
        attrs = dict(_handler_cls=Handler,
                     _service_name=self.service_name)
        name = 'Wrapped{0}'.format(Handler.__name__)
        return WrappedHandlerMeta(name, (object, ), attrs)

    @cached_property
    def wrapped_handler(self):
        """Create wrapped handler instance."""
        return self.WrappedHandler(self.handler)

    @cached_property
    def Processor(self):
        """Create safe processor."""
        cls = symbol_by_name(self.processor_cls)
        attrs = dict(__module__=cls.__module__)
        return type(cls.__name__, (ProcessorMixin, cls), attrs)

    @cached_property
    def processor(self):
        """Create processor instance."""
        return self.Processor(self.wrapped_handler)


class Slot(namedtuple('Slot', 'name listener service')):
    """Combine service and listener together."""

    def __hash__(self):
        return hash(self.__class__) ^ hash(self.name)


class Repository(set):
    """Store existed slots."""

    app = None

    Listener = Listener
    Service = ThriftService

    def register(self, name, processor_cls, handler_cls, **opts):
        """Register new service in repository."""
        # Create listener.
        listener = self.Listener(host=opts.get('host', '0.0.0.0'),
                                 port=opts.get('port'),
                                 backlog=opts.get('backlog'))
        # Create service.
        service = self.Service(service_name=name,
                               processor_cls=processor_cls,
                               handler_cls=handler_cls)
        # Create slot itself.
        slot = Slot(name, listener, service)
        if slot in self:
            raise RegistrationError('Service {0!r} already present in'
                                    ' repository'.format(name))
        self.add(slot)
