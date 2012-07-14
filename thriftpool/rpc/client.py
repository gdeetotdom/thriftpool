from .base import Greenlet, Socket, JsonProtocol, EndpointType, ClientCommands
import logging
import zmq

logger = logging.getLogger(__name__)


class WorkerNotFound(Exception):
    pass


class BaseClient(Greenlet, Socket, JsonProtocol):

    hub = None

    READING = 1
    WRITING = 2

    def __init__(self, ident):
        self.ident = ident
        self.message_prefix = [EndpointType.CLIENT, self.ident]
        self.state = self.WRITING
        super(BaseClient, self).__init__(self.hub.loop, self.hub.ctx,
                                         self.hub.endpoint, zmq.REQ)

    def start(self):
        super(BaseClient, self).start()

    def can_receive(self):
        return self.state == self.READING

    def send(self, command, message):
        assert self.state == self.WRITING, 'client wait response'
        self.socket.send_multipart(self.message_prefix + \
                                    [command, self.encode(message)])
        self.state = self.READING
        self.watcher.start()

        # trigger zeromq socket
        self.try_receive()

    def receive(self):
        assert self.state == self.READING, 'can not read'
        message = self.socket.recv_multipart(zmq.NOBLOCK)
        self.state = self.WRITING
        self.watcher.stop()

        header = message.pop(0)
        assert header == EndpointType.CLIENT, 'wrong header'

        ident = message.pop(0)
        assert self.ident == ident, 'wrong ident'

        command = message.pop(0)

        if command == ClientCommands.REPLY:
            self.switch(self.decode(message.pop(0)))

        elif command == ClientCommands.NOTFOUND:
            self.throw(WorkerNotFound, 'Worker "%s" not found' % ident)

        else:
            logger.error('Invalid message')

    def put(self, message):
        self.send(ClientCommands.REQUEST, message)

    def run(self):
        raise NotImplementedError("subclass responsibility")


class Client(BaseClient):
    pass
