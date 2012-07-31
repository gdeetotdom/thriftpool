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
    def Orchestrator(self):
        return self.subclass_with_self('thriftpool.controllers.orchestrator:Orchestrator')

    @cached_property
    def orchestrator(self):
        return self.Orchestrator()

    @cached_property
    def RemoteBroker(self):
        return self.subclass_with_self('thriftpool.rpc.broker:Broker')

    @cached_property
    def RemoteWorker(self):
        return self.subclass_with_self('thriftpool.rpc.worker:Worker')

    @cached_property
    def RemoteClient(self):
        return self.subclass_with_self('thriftpool.rpc.client:Client')

    @cached_property
    def RemoteProxy(self):
        return self.subclass_with_self('thriftpool.rpc.client:Proxy')
