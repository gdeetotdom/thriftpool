#!/usr/bin/env python

from broker import Broker
from broker.ttypes import Result
from gevent_thrift.server import TGeventStreamServer


class BrokerHandler:
    a = '0' * 256

    def execute(self, task):
        return Result(self.a)


listener = ('localhost', 9090)
handler = BrokerHandler()
processor = Broker.Processor(handler)


server = TGeventStreamServer(listener, processor)

print 'Starting server'
server.serve_forever()
