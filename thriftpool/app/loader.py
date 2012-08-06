"""Contains initializer for application."""
from collections import namedtuple
from thriftpool.utils.functional import cached_property
from thriftpool.utils.imports import symbol_by_name
from thriftpool.utils.other import mk_temp_path
from thriftpool.utils.structures import AttributeDict

__all__ = ['Loader']


class Listener(namedtuple('Listener', 'host port')):
    """Specify which port we should listen."""


class Service(namedtuple('Service', 'processor_cls handler_cls')):
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


class Loader(object):
    """Provide configuration and some callback for main application."""

    app = None

    def __init__(self):
        self._config = AttributeDict(
            DEBUG=True,
            BROKER_ENDPOINT='ipc://{0}'.format(mk_temp_path(prefix='broker')))

        self._slots = [
            Slot(Listener('127.0.0.1', 10051),
                 Service('thriftpool.remote.ThriftPool:Processor',
                         'thriftpool.remote.ThriftPool:Iface')),
        ]

    def get_slots(self):
        return self._slots

    def get_config(self):
        return self._config

    def on_before_init(self):
        self.app.log.setup()

    def on_start(self):
        """Called before controller starts."""
        pass

    def on_shutdown(self):
        """Called after controller shutdown."""
        pass
