"""Main factory for this library. Single entry point for all application."""

from billiard.util import register_after_fork
import zmq

from thriftpool.app.config import Configuration
from thriftpool.utils.functional import cached_property
from thriftpool.utils.mixin import SubclassMixin

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

    def _after_fork(self, obj_):
        del self.hub
        del self.context

    @cached_property
    def Loader(self):
        """"""
        return self.subclass_with_self(self.loader_cls)

    @cached_property
    def loader(self):
        return self.Loader()

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
    def SlotsRepository(self):
        """Create bounded slots repository from :class:`.slots:Repository`."""
        return self.subclass_with_self('thriftpool.app.slots:Repository')

    @cached_property
    def config(self):
        """Empty application configuration."""
        return Configuration(self.loader.get_config())

    @cached_property
    def slots(self):
        """Create repository of service slots. By default it is empty."""
        return self.SlotsRepository()

    def finalize(self):
        """Make some steps before application startup."""
        # Register existed services.
        for params in self.config.SLOTS:
            self.slots.register(**params)
        # Setup logging for whole application.
        self.log.setup()

    @cached_property
    def Hub(self):
        return self.subclass_with_self('thriftpool.app.hub:Hub')

    @cached_property
    def hub(self):
        return self.Hub()

    @cached_property
    def context(self):
        return zmq.Context()

    @cached_property
    def OrchestratorController(self):
        return self.subclass_with_self('thriftpool.controllers.orchestrator:OrchestratorController')

    @cached_property
    def orchestrator(self):
        return self.OrchestratorController()

    @cached_property
    def CartridgeController(self):
        return self.subclass_with_self('thriftpool.controllers.cartridge:CartridgeController')

    @cached_property
    def ListenerController(self):
        return self.subclass_with_self('thriftpool.controllers.listener:ListenerController')

    @cached_property
    def WorkerController(self):
        return self.subclass_with_self('thriftpool.controllers.worker:WorkerController')

    @cached_property
    def MDPBroker(self):
        return self.subclass_with_self('thriftpool.mdp.broker:Broker')

    @cached_property
    def MDPService(self):
        return self.subclass_with_self('thriftpool.mdp.service:Service')

    @cached_property
    def MDPClient(self):
        return self.subclass_with_self('thriftpool.mdp.client:Client')

    @cached_property
    def MDPProxy(self):
        return self.subclass_with_self('thriftpool.mdp.client:Proxy')
