from base import factory
from broker import Broker as TBroker
from broker.ttypes import Result
from setproctitle import setproctitle


class BrokerHandler:
    a = '0' * 2048

    def execute(self, task):
        return Result(self.a)


def main():
    processor = TBroker.Processor(BrokerHandler())
    worker = factory.Worker(processor)
    worker.start()
    worker.join()


if __name__ == '__main__':
    setproctitle('[worker]')
    main()
    #import cProfile
    #cProfile.runctx("main()", globals(), locals(), "worker.prof")
