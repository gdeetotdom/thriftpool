from __future__ import absolute_import
from collections import deque
from thriftpool.components.base import StartStopComponent
from thriftpool.remote.ThriftPool import Processor, Iface
from thriftpool.utils.threads import SimpleDaemonThread

__all__ = ['PoolComponent']


class Handler(Iface):
    def ping(self):
        pass


class Pool(object):
    """Maintain pool of thrift service."""

    def __init__(self, socket_zmq):
        self.socket_zmq = socket_zmq
        self.pool = deque()

    def start(self):
        pass

    def stop(self):
        while self.pool:
            worker, thread = self.pool.popleft()
            worker.stop()
            thread.stop()

    def add(self, backend):
        processor = Processor(Handler())
        worker = self.socket_zmq.Worker(processor, backend)
        thread = SimpleDaemonThread(target=worker.start)
        thread.start()
        self.pool.append((worker, thread))


class PoolComponent(StartStopComponent):

    name = 'worker.pool'

    def create(self, parent):
        pool = parent.pool = Pool(parent.socket_zmq)
        return pool
