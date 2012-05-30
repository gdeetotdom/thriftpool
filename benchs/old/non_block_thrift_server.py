#!/usr/bin/env python

from broker import Broker
from broker.ttypes import Result
from thrift.transport import TTransport
from thrift.server.TNonblockingServer import TNonblockingServer

# Thrift files
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer
from thrift.protocol.TBinaryProtocol import TBinaryProtocolFactory


class BrokerHandler:
    a = '0' * 256

    def execute(self, task):
        return Result(self.a)


listener = ('localhost', 9090)
handler = BrokerHandler()
processor = Broker.Processor(handler)
transport = TSocket.TServerSocket(listener[0], listener[1])
tfactory = TBinaryProtocolFactory()
pfactory = TBinaryProtocolFactory()

# set server
server = TNonblockingServer(processor, transport, tfactory, pfactory)

print 'Starting server'
server.serve()
