from thriftpool.utils.functional import cached_property
from thriftpool.utils.mixin import SubclassMixin
from thriftpool.utils.structures import AttributeDict
import zmq

__all__ = ['ThriftPool']


class ThriftPool(SubclassMixin):

    @cached_property
    def Controller(self):
        return self.subclass_with_self('thriftpool.worker.controller:Controller')

    @cached_property
    def Hub(self):
        return self.subclass_with_self('thriftpool.app.hub:Hub')

    @cached_property
    def Broker(self):
        return self.subclass_with_self('thriftpool.rpc.broker:Broker')

    @cached_property
    def Client(self):
        return self.subclass_with_self('thriftpool.rpc.client:Client')

    @cached_property
    def Proxy(self):
        return self.subclass_with_self('thriftpool.rpc.proxy:Proxy')

    @cached_property
    def Worker(self):
        return self.subclass_with_self('thriftpool.rpc.worker:Worker')

    @cached_property
    def controller(self):
        return self.Controller()

    @cached_property
    def config(self):
        return AttributeDict({'BROKER_ENDPOINT': 'tcp://*:5556'})

    @cached_property
    def hub(self):
        return self.Hub()

    @cached_property
    def ctx(self):
        return zmq.Context()
