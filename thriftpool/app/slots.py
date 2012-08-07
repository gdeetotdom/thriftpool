"""Implement service repository."""
from collections import namedtuple
from thriftpool.utils.functional import cached_property
from thriftpool.utils.imports import symbol_by_name
from thriftpool.utils.other import mk_temp_path

__all__ = ['Repository']


class Listener(namedtuple('Listener', 'host port backlog')):
    """Specify which port we should listen."""

    def __init__(self, host, port, backlog):
        super(Listener, self).__init__(host, int(port), backlog)


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


class Slot(object):
    """Combine service and listener together."""

    def __init__(self, listener, service):
        self.listener = listener
        self.service = service
        self.backend = 'ipc://{0}'.format(mk_temp_path(prefix='slot'))


class Repository(set):
    """Store existed slots."""

    def __init__(self, config):
        super(Repository, self).__init__()

