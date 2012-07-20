from struct import Struct
from greenlet import GreenletExit
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

    def decode(self, body):
        return simplejson.loads(body)

    def encode(self, obj):
        return simplejson.dumps(obj)


class Base(JsonProtocol):

    def __init__(self, app):
        self.app = app
        super(Base, self).__init__()

    @cached_property
    def greenlet(self):
        return self.app.hub.Greenlet(run=self.run)

    def start(self):
        self.greenlet.start()

    def run(self):
        self.initialize()
        try:
            while True:
                self.loop()
        except GreenletExit:
            self.destruct()

    def initialize(self):
        raise NotImplementedError()

    def loop(self):
        raise NotImplementedError()

    def destruct(self):
        pass

    def stop(self):
        self.greenlet.kill()
