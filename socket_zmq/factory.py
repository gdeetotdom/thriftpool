from gevent.greenlet import Greenlet
from gevent.socket import socket
import zmq
from socket_zmq.server import StreamServer
from thrift.protocol.TBinaryProtocol import TBinaryProtocolFactory
from thrift.transport import TTransport
from zmq.devices import ThreadDevice
import logging
import multiprocessing
import _socket


class Server(object):

    def __init__(self, address, context, frontend):
        self.socket = self.get_listener(address)
        self.server = StreamServer(context, frontend, self.socket)

    def get_listener(self, address, backlog=50, family=_socket.AF_INET):
        """A shortcut to create a TCP socket, bind it and put it into listening state."""
        sock = socket(family=family)
        sock.bind(address)
        sock.listen(backlog)
        sock.setblocking(0)
        return sock

    def serve_forever(self):
        self.server.serve_forever()

    def stop(self):
        self.server.stop()


class Worker(object):

    def __init__(self, context, backend, processor):
        self.context = context
        self.backend = backend
        self.in_protocol = TBinaryProtocolFactory()
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
            socket.send('')
        else:
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
        self.context = zmq.Context(multiprocessing.cpu_count())

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
