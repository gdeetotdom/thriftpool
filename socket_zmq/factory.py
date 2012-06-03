from gevent.greenlet import Greenlet
from gevent.pool import Pool
from gevent.server import StreamServer
from socket_zmq.connection import Connection
from gevent_zeromq import zmq
from thrift.protocol.TBinaryProtocol import TBinaryProtocolFactory
from thrift.transport import TTransport
from zmq.devices import ThreadDevice
import logging


class Server(StreamServer):

    def __init__(self, listener, context, frontend, **kwargs):
        self.context = context
        self.frontend = frontend
        self.pool = Pool(size=1024)
        super(Server, self).__init__(listener=listener, spawn=self.pool,
                                     **kwargs)

    def create_socket(self):
        client_socket = self.context.socket(zmq.REQ)
        client_socket.connect(self.frontend)
        return client_socket

    def handle(self, socket, address):
        zmq_socket = self.create_socket()
        connection = Connection(socket, zmq_socket)


class Worker(Greenlet):

    def __init__(self, context, backend, processor):
        self.context = context
        self.backend = backend
        self.in_protocol = TBinaryProtocolFactory()
        self.out_protocol = self.in_protocol
        self.processor = processor
        Greenlet.__init__(self)

    def create_socket(self):
        worker_socket = self.context.socket(zmq.REP)
        worker_socket.connect(self.backend)
        return worker_socket

    def process(self, socket):
        itransport = TTransport.TMemoryBuffer(socket.recv())
        otransport = TTransport.TMemoryBuffer()
        iprot = self.in_protocol.getProtocol(itransport)
        oprot = self.out_protocol.getProtocol(otransport)

        try:
            self.processor.process(iprot, oprot)
        except Exception, exc:
            logging.exception(exc)
            socket.send('')
        else:
            socket.send(otransport.getvalue())

    def _run(self):
        socket = self.create_socket()
        try:
            while True:
                self.process(socket)
        finally:
            socket.close()


class Factory(object):

    def __init__(self, backend):
        self.context = zmq.Context()

        self.frontend = "inproc://frontend_%s" % id(self)
        self.backend = backend

        super(Factory, self).__init__()

    def Device(self):
        device = ThreadDevice(zmq.QUEUE, zmq.ROUTER, zmq.DEALER)
        device.context_factory = lambda: self.context
        device.bind_in(self.frontend)
        device.bind_out(self.backend)

        return device

    def Server(self, listener):
        server = Server(listener, self.context, self.frontend)

        return server

    def Worker(self, processor):
        worker = Worker(self.context, self.backend, processor)

        return worker
