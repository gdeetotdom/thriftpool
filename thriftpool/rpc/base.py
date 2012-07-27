from greenlet import GreenletExit
from struct import Struct
from thriftpool.utils.functional import cached_property

try:
    from cPickle import loads, dumps
except ImportError:
    from pickle import loads, dumps

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


class Protocol(object):

    EndpointType = EndpointType
    ClientCommands = ClientCommands
    WorkerCommands = WorkerCommands

    def decode(self, body):
        return loads(body)

    def encode(self, obj):
        return dumps(obj)


class Base(Protocol):

    app = None

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
