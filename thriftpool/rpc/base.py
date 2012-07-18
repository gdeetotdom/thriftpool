from struct import Struct
import simplejson
from thriftpool.utils.functional import cached_property

struct = Struct('!B')


class UnknownCommand(Exception):
    pass


class WorkerNotFound(Exception):
    pass


class EndpointType(object):
    CLIENT = struct.pack(0x1)
    WORKER = struct.pack(0x2)


class ClientCommands(object):
    REQUEST = struct.pack(0x1)
    REPLY = struct.pack(0x2)
    NOTFOUND = struct.pack(0x3)


class WorkerCommands(object):
    READY = struct.pack(0x1)
    REQUEST = struct.pack(0x2)
    REPLY = struct.pack(0x3)
    DISCONNECT = struct.pack(0x4)


class BaseProtocol(object):

    EndpointType = EndpointType
    ClientCommands = ClientCommands
    WorkerCommands = WorkerCommands

    def decode(self, body):
        raise NotImplementedError()

    def encode(self, obj):
        raise NotImplementedError()


class JsonProtocol(BaseProtocol):

    def __init__(self):
        self.decoder = simplejson.JSONDecoder()
        self.encoder = simplejson.JSONEncoder()
        super(JsonProtocol, self).__init__()

    def decode(self, body):
        return self.decoder.decode(body)

    def encode(self, obj):
        return self.encoder.encode(obj)


class Base(JsonProtocol):

    app = None

    @cached_property
    def greenlet(self):
        return self.app.hub.Greenlet(run=self.run)

    def start(self):
        self.greenlet.start()

    def run(self):
        self.initialize()
        while True:
            self.loop()

    def initialize(self):
        raise NotImplementedError()

    def loop(self):
        raise NotImplementedError()

    def stop(self):
        self.greenlet.kill()
