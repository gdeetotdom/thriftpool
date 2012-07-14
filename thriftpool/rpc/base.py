from greenlet import greenlet
from struct import Struct
from thriftpool.utils.functional import cached_property
import logging
import pyev
import simplejson
import zmq

logger = logging.getLogger(__name__)
struct = Struct('!B')


class Greenlet(object):

    hub = None

    @cached_property
    def greenlet(self):
        return greenlet(run=self.run)

    def start(self):
        super(Greenlet, self).start()
        self.greenlet.switch()

    def switch(self, *args, **kwargs):
        assert not self.greenlet.dead, 'greenlet is dead'
        return self.greenlet.switch(*args, **kwargs)

    def throw(self, typ, val, tb=None):
        self.greenlet.throw(typ, val, tb)

    def get(self):
        return self.hub.greenlet.switch()

    def put(self, message):
        self.hub.switch(message)

    def run(self):
        raise NotImplementedError()


class BaseProtocol(object):

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


class Watcher(object):

    def __init__(self, loop, fileno):
        self.loop = loop
        self.watcher = pyev.Io(fileno, pyev.EV_READ, self.loop, self.on_readable)
        super(Watcher, self).__init__()

    def start(self):
        self.watcher.start()

    def on_readable(self, watcher, revents):
        """Called when file descriptor become readable."""
        raise NotImplementedError()

    def close(self):
        """Closes and unset watcher."""
        self.watcher.stop()
        self.watcher = None


class Socket(Watcher):

    def __init__(self, loop, ctx, endpoint, socket_type):
        self.ctx = ctx
        self.endpoint = endpoint
        self.socket = self.ctx.socket(socket_type)
        super(Socket, self).__init__(loop, self.socket.fd)

    def start(self):
        super(Socket, self).start()
        self.socket.connect(self.endpoint)

    def can_receive(self):
        return True

    def try_receive(self):
        while self.can_receive():
            try:
                self.receive()
            except zmq.ZMQError as exc:
                if exc.errno == zmq.EAGAIN:
                    break
                raise

    def on_readable(self, watcher, revents):
        try:
            self.try_receive()
        except Exception as exc:
            logger.exception(exc)

    def receive(self):
        raise NotImplementedError()

    def close(self):
        self.socket.close()
        super(Socket, self).close()


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
