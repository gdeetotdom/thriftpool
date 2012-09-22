from thriftpool.remote.ThriftPool import Iface
from thriftpool.remote.ThriftPool import Processor
from thriftpool import thriftpool


@thriftpool.register(processor=Processor, port=45000)
class Handler(Iface):

    def ping(self):
        pass
