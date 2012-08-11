from __future__ import absolute_import
from socket_zmq.utils import cached_property
from struct import Struct
from thrift.protocol.TBinaryProtocol import (
    TBinaryProtocolAcceleratedFactory as TProtocolFactory)
from thrift.transport.TTransport import TMemoryBuffer
from thriftpool.components.base import StartStopComponent
from thriftpool.utils.mixin import SubclassMixin
from thriftpool.utils.threads import LoopThread
from zmq.core.poll import Poller
import logging
import zmq
from thriftpool.utils.logs import LogsMixin

__all__ = ['PoolComponent']

logger = logging.getLogger(__name__)

RCVTIMEO = 100


class Connection(object):
    """Process new requests and send response to listener."""

    pool = None

    def __init__(self, backend, processor):
        self.formatter = Struct('!?')
        self.backend = backend
        self.processor = processor
        self.out_factory = self.in_factory = TProtocolFactory()

    @cached_property
    def socket(self):
        socket = self.pool.context.socket(zmq.REP)
        socket.connect(self.backend)
        self.pool.poller.register(socket, zmq.POLLIN)
        return socket

    def process(self):
        socket = self.socket
        in_transport = TMemoryBuffer(socket.recv(flags=zmq.NOBLOCK))
        out_transport = TMemoryBuffer()

        in_prot = self.in_factory.getProtocol(in_transport)
        out_prot = self.out_factory.getProtocol(out_transport)
        success = True

        try:
            self.processor.process(in_prot, out_prot)
        except Exception, exc:
            logger.exception(exc)
            success = False

        socket.send(self.formatter.pack(success), flags=zmq.SNDMORE)
        socket.send(out_transport.getvalue())

    def close(self):
        self.pool.poller.unregister(self.socket)
        self.socket.close()


class Hub(LoopThread, SubclassMixin):
    """Maintain pool of thrift service."""

    def __init__(self, app, max_workers=None):
        super(Hub, self).__init__()
        self.app = app
        self.poller = Poller()
        self.connections = {}

    @cached_property
    def context(self):
        return self.app.context

    @cached_property
    def Connection(self):
        return self.subclass_with_self(Connection, attribute='pool')

    def loop(self):
        for socket, state in self.poller.poll(RCVTIMEO):
            connection = self.connections[socket]
            try:
                connection.process()
            except zmq.ZMQError as exc:
                if exc.errno != zmq.EAGAIN:
                    raise

    def on_stop(self):
        for connection in self.connections.values():
            connection.close()
        self.connections = {}

    def register(self, backend, processor):
        connection = self.Connection(backend, processor)
        self.connections[connection.socket] = connection


class Pool(LogsMixin):
    """Maintain pool of hub threads."""

    def __init__(self, app, threads=10):
        self.hubs = [Hub(app) for i in xrange(threads)]

    def start(self):
        for hub in self.hubs:
            hub.start()

    def stop(self):
        for hub in self.hubs:
            hub.stop()

    def register(self, name, service, backend):
        self._info("Start processing service '%s'.", name)
        for hub in self.hubs:
            hub.register(backend, service.processor)


class PoolComponent(StartStopComponent):

    name = 'worker.pool'

    def create(self, parent):
        pool = parent.pool = Pool(parent.app)
        return pool
