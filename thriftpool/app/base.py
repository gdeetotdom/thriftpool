from thriftpool.utils.functional import cached_property
from thriftpool.utils.mixin import SubclassMixin

__all__ = ['ThriftPool']


class ThriftPool(SubclassMixin):

    #: Describe which class should used as application controller.
    controller_cls = 'thriftpool.worker.controller:Controller'

    @cached_property
    def Controller(self):
        return self.subclass_with_self(self.controller_cls)

    @cached_property
    def controller(self):
        return self.Controller()
