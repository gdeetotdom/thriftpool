from __future__ import absolute_import
from socket_zmq.utils import cached_property
from struct import Struct
from thrift.protocol.TBinaryProtocol import TBinaryProtocolAcceleratedFactory
from thrift.transport.TTransport import TMemoryBuffer
from thriftpool.components.base import StartStopComponent
from thriftpool.utils.logs import LogsMixin
from thriftpool.utils.mixin import SubclassMixin
from thriftpool.utils.threads import LoopThread
from zmq.core.poll import Poller
import logging
import zmq

__all__ = ['PoolComponent']

logger = logging.getLogger(__name__)

RCVTIMEO = 100


class Hub(LogsMixin, LoopThread):
    """Process new requests and send response to listener."""

    pool = None

    def __init__(self):
        self.formatter = Struct('!?')
        self.out_factory = self.in_factory = TBinaryProtocolAcceleratedFactory()
        self.poller = Poller()
        super(Hub, self).__init__()

    def on_start(self):
        self.poller.register(self.socket, zmq.POLLIN)

    def loop(self):
        if not self.poller.poll(RCVTIMEO):
            return
        while True:
            try:
                self.process()
            except zmq.ZMQError as exc:
                if exc.errno == zmq.EAGAIN:
                    break
                else:
                    raise

    def on_stop(self):
        self.poller.unregister(self.socket)
        self.socket.close()

    @cached_property
    def socket(self):
        socket = self.pool.context.socket(zmq.REP)
        socket.connect(self.pool.backend_endpoint)
        return socket

    def process(self):
        socket = self.socket
        request = socket.recv_multipart(flags=zmq.NOBLOCK)
        in_transport = TMemoryBuffer(request[1])
        out_transport = TMemoryBuffer()

        in_prot = self.in_factory.getProtocol(in_transport)
        out_prot = self.out_factory.getProtocol(out_transport)

        success = True
        try:
            self.pool.processors[request[0]].process(in_prot, out_prot)
        except Exception, exc:
            self._exception(exc)
            success = False

        socket.send_multipart((self.formatter.pack(success),
                               out_transport.getvalue()))


class Pool(LogsMixin, SubclassMixin):
    """Maintain pool of hub threads."""

    def __init__(self, app, backend_endpoint, hubs=None):
        self.app = app
        self.backend_endpoint = backend_endpoint
        self.processors = {}
        self.hubs = [self.Hub() for i in xrange(hubs or 10)]
        super(Pool, self).__init__()

    @property
    def context(self):
        return self.app.context

    @cached_property
    def Hub(self):
        return self.subclass_with_self(Hub, attribute='pool')

    def _foreach(self, func):
        for hub in self.hubs:
            func(hub)

    def start(self):
        self._foreach(lambda hub: hub.start())

    def stop(self):
        self._foreach(lambda hub: hub.stop())

    def register(self, name, processor):
        self._info("Start processing service '%s'.", name)
        self.processors[name] = processor


class PoolComponent(StartStopComponent):

    name = 'worker.pool'

    def create(self, parent):
        pool = parent.pool = Pool(parent.app, parent.backend_endpoint)
        return pool
