from billiard.util import register_after_fork
from thriftpool.utils.functional import cached_property
from thriftpool.utils.mixin import SubclassMixin
import zmq

__all__ = ['ThriftPool']


class ThriftPool(SubclassMixin):

    def __init__(self):
        register_after_fork(self, self._after_fork)
        super(ThriftPool, self).__init__()

    @cached_property
    def Logging(self):
        return self.subclass_with_self('thriftpool.app.log:Logging')

    @cached_property
    def log(self):
        return self.Logging()

    @cached_property
    def Hub(self):
        return self.subclass_with_self('thriftpool.app.hub:Hub')

    @cached_property
    def hub(self):
        return self.Hub()

    def _after_fork(self, obj_):
        del self.hub
        del self.ctx

    @cached_property
    def Loader(self):
        return self.subclass_with_self('thriftpool.app.loader:Loader')

    @cached_property
    def loader(self):
        return self.Loader()

    @cached_property
    def config(self):
        return self.loader.get_config()

    @cached_property
    def ctx(self):
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
