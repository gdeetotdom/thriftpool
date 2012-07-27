from .base import Protocol, UnknownCommand, WorkerNotFound
from thriftpool.utils.functional import cached_property
from thriftpool.utils.socket import Socket
import logging
import zmq

logger = logging.getLogger(__name__)


class Client(Protocol):

    app = None

    def __init__(self, ident):
        self.ident = ident
        self.message_prefix = [self.EndpointType.CLIENT, self.ident]
        super(Client, self).__init__()

    @cached_property
    def socket(self):
        socket = Socket(self.app.hub, self.app.ctx, zmq.REQ)
        socket.connect(self.app.config.BROKER_ENDPOINT)
        return socket

    def close(self):
        self.socket.close()

    def send(self, command, message):
        self.socket.send_multipart(self.message_prefix + \
                                    [command, self.encode(message)])

    def read_request(self):
        message = self.socket.recv_multipart()

        header = message.pop(0)
        assert header == self.EndpointType.CLIENT, 'wrong header'

        ident = message.pop(0)
        assert self.ident == ident, 'wrong ident'

        command = message.pop(0)

        if command == self.ClientCommands.REPLY:
            return self.decode(message.pop(0))

        elif command == self.ClientCommands.NOTFOUND:
            raise WorkerNotFound('Worker "%s" not found' % ident)

        else:
            raise UnknownCommand()

    def send_reply(self, result):
        self.send(self.ClientCommands.REQUEST, result)


class Proxy(object):
    """Proxy handler."""

    app = None

    def __init__(self, ident):
        self.__client = self.app.RemoteClient(ident)

    def __getattr__(self, name):
        client = self.__client

        def inner(*args, **kwargs):
            request = {'method': name, 'args': args, 'kwargs': kwargs}
            client.send_reply(request)
            response = client.read_request()
            if 'result' in response:
                return response['result']
            elif 'exc' in response:
                raise response['exc']
            else:
                raise AssertionError('Wrong response')

        inner.__name__ = name
        return inner
