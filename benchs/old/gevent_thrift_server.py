#!/usr/bin/env python

from broker import Broker
from broker.ttypes import Result
from socket_zmq.thrift_server import TGeventStreamServer
from gevent.greenlet import Greenlet
from setproctitle import setproctitle


class BrokerHandler:
    a = '0' * 256

    def execute(self, task):
        return Result(self.a)


listener = ('localhost', 9090)
handler = BrokerHandler()
processor = Broker.Processor(handler)


server = TGeventStreamServer(listener, processor)


def main():
    print 'Starting server'
    Greenlet(server.stop).start_later(30)
    server.serve_forever()

if __name__ == '__main__':
    setproctitle('[server]')
    #main()
    import cProfile
    cProfile.runctx("main()", globals(), locals(), "server.prof")
