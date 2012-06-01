# cython: profile=True
from .connection import Connection
from gevent.pool import Pool
from gevent.server import StreamServer
from thrift.protocol.TBinaryProtocol import TBinaryProtocolFactory
from thrift.transport import TTransport
import logging


class TGeventStreamServer(StreamServer):
    def __init__(self, listener, processor, inputProtocolFactory=None,
            outputProtocolFactory=None, pool_size=None):
        self.processor = processor
        self.in_protocol = inputProtocolFactory or TBinaryProtocolFactory()
        self.out_protocol = outputProtocolFactory or self.in_protocol
        self.pool = Pool(size=pool_size or 1024)
        StreamServer.__init__(self, listener, spawn=self.pool)

    def process(self, connection):
        content = connection.get_request()
        if connection.is_closed():
            return

        itransport = TTransport.TMemoryBuffer(content)
        otransport = TTransport.TMemoryBuffer()
        iprot = self.in_protocol.getProtocol(itransport)
        oprot = self.out_protocol.getProtocol(otransport)

        try:
            self.processor.process(iprot, oprot)
        except Exception, exc:
            logging.exception(exc)
            connection.set_reply('', is_successed=False)
        else:
            connection.set_reply(otransport.getvalue())

    def handle(self, socket, address):
        connection = Connection(socket)

        while not connection.is_closed():
            self.process(connection)
