from thriftpool.remote.ThriftPool import Iface
from thriftpool.remote.ThriftPool import Processor
from thriftpool import thriftpool


@thriftpool.register(processor=Processor)
class Handler(Iface):

    def ping(self):
        pass
