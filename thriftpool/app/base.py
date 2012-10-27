"""Main factory for this library. Single entry point for all application."""
from __future__ import absolute_import

import inspect

from thriftworker.utils.decorators import cached_property
from thriftworker.app import ThriftWorker

from thriftpool.app.config import Configuration
from thriftpool.exceptions import RegistrationError
from thriftpool.utils.mixin import SubclassMixin
from thriftpool.utils.imports import symbol_by_name

from ._state import set_current_app

try:
    from billiard.util import register_after_fork
except ImportError:
    register_after_fork = lambda *args: None

__all__ = ['ThriftPool']


class ThriftPool(SubclassMixin):
    """Main entry point for this application."""

    #: Default loader for this application. Must provide configuration
    #: for it.
    loader_cls = 'thriftpool.app.loader:Loader'

    def __init__(self):
        # we must delete some entries after work
        register_after_fork(self, self._after_fork)
        super(ThriftPool, self).__init__()

        # set current application as default
        set_current_app(self)

    def _after_fork(self, obj_):
        # Reset needed resources after fork."
        pass

    @cached_property
    def Loader(self):
        """Default loader class."""
        return self.subclass_with_self(self.loader_cls)

    @cached_property
    def loader(self):
        return self.Loader()

    @cached_property
    def config(self):
        """Empty application configuration."""
        return Configuration(self.loader.get_config())

    @cached_property
    def Logging(self):
        """Create bounded logging initialize class from :class:`.log.Logging`.
        We will call :meth:`.log.Logging.setup` on finalization to setup
        logging.

        """
        return self.subclass_with_self('thriftpool.app.log:Logging')

    @cached_property
    def log(self):
        """Instantiate logging initializer from bounded class."""
        return self.Logging()

    @cached_property
    def Repository(self):
        """Create bounded slots repository from :class:`.slots:Repository`."""
        return self.subclass_with_self('thriftpool.app.slots:Repository')

    @cached_property
    def slots(self):
        """Create repository of service slots. By default it is empty."""
        return self.Repository()

    def finalize(self):
        """Make some steps before application startup."""
        # Setup logging for whole application.
        self.log.setup()
        # Load all needed modules.
        self.loader.preload_modules()
        # Register existed services.
        for params in self.config.SLOTS:
            self.slots.register(**params)

    @cached_property
    def protocol_factory(self):
        """Create handler instance."""
        ProtocolFactory = symbol_by_name(self.config.PROTOCOL_FACTORY_CLS)
        return ProtocolFactory()

    @cached_property
    def thriftworker(self):
        return ThriftWorker(port_range=self.config.SERVICE_PORT_RANGE,
                            protocol_factory=self.protocol_factory)

    @cached_property
    def WorkerController(self):
        return self.subclass_with_self('thriftpool.controllers.worker:WorkerController')

    @cached_property
    def Worker(self):
        return self.subclass_with_self('thriftpool.app.worker:Worker')

    def register(self, *args, **options):
        """Register new handler."""

        def inner_register_handler(**options):

            def _register_handler(cls):
                # Check that handler is a class.
                if not inspect.isclass(cls):
                    raise RegistrationError('Object "{0!r}" is not a class'
                                            .format(cls))
                # Get processor for handler.
                processor = options.pop('processor', None)
                if processor is None:
                    raise RegistrationError('Processor for handler "{0!r}"'
                                            ' not specified'.format(cls))
                # Detect name for handler.
                name = options.pop('name', processor.__module__)
                self.slots.register(name=name,
                                    handler_cls=cls,
                                    processor_cls=processor,
                                    **options)
                return cls

            return _register_handler

        if len(args) == 1 and callable(args[0]):
            return inner_register_handler(**options)(*args)
        return inner_register_handler(**options)

    @cached_property
    def request_stack(self):
        """Store current requests."""
        RequestStack = symbol_by_name('thriftpool.request.stack:RequestStack')
        return RequestStack()
