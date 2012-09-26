from thriftpool.remote.ThriftPool import Iface
from thriftpool.remote.ThriftPool import Processor
from thriftpool.base import BaseHandler


class Handler(BaseHandler, Iface):

    class options:
        processor = Processor
        port = 45000

    def ping(self):
        pass
