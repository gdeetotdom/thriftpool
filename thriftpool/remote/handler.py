from thriftpool.remote.ThriftPool import Iface
from thriftpool.remote.ThriftPool import Processor
from thriftpool.base import BaseHandler


class Handler(BaseHandler, Iface):

    class options:
        name = 'ThriftPool'
        processor = Processor

    def ping(self):
        pass

    def echoString(self, s):
        return s
