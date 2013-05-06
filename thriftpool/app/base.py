"""Main factory for this library. Single entry point for all application."""
from __future__ import absolute_import

import inspect
from threading import RLock

from gaffer.manager import Manager

from thriftworker.utils.decorators import cached_property
from thriftworker.utils.imports import instantiate
from thriftworker.app import ThriftWorker

from thriftpool.app.config import Configuration
from thriftpool.exceptions import RegistrationError
from thriftpool.utils.mixin import SubclassMixin

from ._state import set_current_app

__all__ = ['ThriftPool']


def _unpickle_app(cls, changes, slots):
    app = cls()
    app.config.update(changes)
    app.slots = slots
    app.loader.after_unpickling()
    return app


class ThriftPool(SubclassMixin):
    """Main entry point for this application."""

    #: Default loader for this application. Must provide configuration
    #: for it.
    loader_cls = 'thriftpool.app.loader:Loader'

    #: What class should be used for logging setup.
    logging_cls = 'thriftpool.app.log:Logging'

    #: Repository for registered slots.
    repo_cls = 'thriftpool.app.slots:Repository'

    #: Manager controller class.
    manager_cls = 'thriftpool.controllers.manager:ManagerController'

    #: Worker controller class.
    worker_cls = 'thriftpool.controllers.worker:WorkerController'

    #: Specify daemonizing behavior.
    daemon_cls = 'thriftpool.app.daemon:Daemon'

    #: Store active requests here.
    request_stack_cls = 'thriftpool.request.stack:RequestStack'

    def __init__(self):
        self._finalized = False
        self._finalize_mutex = RLock()
        super(ThriftPool, self).__init__()

        # set current application as default
        set_current_app(self)

    def __reduce__(self):
        # Reduce only pickles the configuration changes,
        # so the default configuration doesn't have to be passed
        # between processes.
        return (_unpickle_app, (self.__class__, self.config._changes,
                                self.slots))

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
        return self.subclass_with_self(self.logging_cls)

    @cached_property
    def log(self):
        """Instantiate logging initializer from bounded class."""
        return self.Logging()

    @cached_property
    def Repository(self):
        """Create bounded slots repository from :class:`.slots:Repository`."""
        return self.subclass_with_self(self.repo_cls)

    @cached_property
    def slots(self):
        """Create repository of service slots. By default it is empty."""
        return self.Repository()

    def finalize(self):
        """Make some steps before application startup."""
        with self._finalize_mutex:
            if self._finalized:
                return
            # Setup logging for whole application.
            self.log.setup()
            # Load all needed modules.
            self.loader.preload_modules()
            # Register existed services.
            for params in self.config.SLOTS:
                self.slots.register(**params)
            self._finalized = True

    @cached_property
    def protocol_factory(self):
        """Create handler instance."""
        return instantiate(self.config.PROTOCOL_FACTORY_CLS)

    @cached_property
    def thriftworker(self):
        return ThriftWorker(port_range=self.config.SERVICE_PORT_RANGE,
                            protocol_factory=self.protocol_factory,
                            pool_size=self.config.CONCURRENCY)

    @property
    def loop(self):
        return self.thriftworker.loop

    @property
    def hub(self):
        return self.thriftworker.hub

    @cached_property
    def gaffer_manager(self):
        """Create process manager."""
        return Manager(loop=self.loop)

    @cached_property
    def ManagerController(self):
        return self.subclass_with_self(self.manager_cls)

    @cached_property
    def WorkerController(self):
        return self.subclass_with_self(self.worker_cls)

    @cached_property
    def Daemon(self):
        return self.subclass_with_self(self.daemon_cls)

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
        return instantiate(self.request_stack_cls)
