"""Main factory for this library. Single entry point for all application."""
from billiard.util import register_after_fork
import pyev
import zmq

from thriftpool.app.config import Configuration
from thriftpool.utils.functional import cached_property
from thriftpool.utils.mixin import SubclassMixin
from thriftpool.utils.other import cpu_count
from socket_zmq.app import SocketZMQ

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
        del self.socket_zmq
        del self.context
        del self.loop

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
    def context(self):
        return zmq.Context(cpu_count())

    @cached_property
    def loop(self):
        return pyev.Loop(debug=self.config.DEBUG)

    @cached_property
    def socket_zmq(self):
        return SocketZMQ(context=self.context,
                         loop=self.loop,
                         frontend_endpoint=self.config.FRONTEND_ENDPOINT,
                         backend_endpoint=self.config.BACKEND_ENDPOINT)

    @cached_property
    def OrchestratorController(self):
        return self.subclass_with_self('thriftpool.controllers.orchestrator:OrchestratorController')

    @cached_property
    def orchestrator(self):
        return self.OrchestratorController()
