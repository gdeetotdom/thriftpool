import zmq
from socket_zmq import App
from thrift.protocol.TBinaryProtocol import TBinaryProtocolAcceleratedFactory
from thrift.transport import TTransport
import logging
from struct import Struct

logging.basicConfig(level=logging.DEBUG)


class Server(object):

    def __init__(self, address, frontend, backend):
        self.frontend = frontend
        self.backend = backend
        self.address = address
        self.app = App()
        self.controller = self.app.controller
        self.controller.register(self.app.ProxyComponent(address, frontend, backend))

    def serve_forever(self):
        self.controller.serve_forever()


class Worker(object):

    def __init__(self, context, backend, processor):
        self.struct = Struct('!?')
        self.context = context
        self.backend = backend
        self.in_protocol = TBinaryProtocolAcceleratedFactory()
        self.out_protocol = self.in_protocol
        self.processor = processor

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
            socket.send(self.struct.pack(False), flags=zmq.SNDMORE)
            socket.send('')
        else:
            socket.send(self.struct.pack(True), flags=zmq.SNDMORE)
            socket.send(otransport.getvalue())

    def run(self):
        socket = self.create_socket()
        try:
            while True:
                self.process(socket)
        finally:
            socket.close()


class Factory(object):

    def __init__(self, backend):
        self.context = zmq.Context()

        self.frontend = 'inproc://frontend'
        self.backend = backend

        super(Factory, self).__init__()

    def Server(self, listener):
        server = Server(listener, self.frontend, self.backend)

        return server

    def Worker(self, processor):
        worker = Worker(self.context, self.backend, processor)

        return worker
