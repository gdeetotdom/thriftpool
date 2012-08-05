from .base import Base, UnknownCommand
from thriftpool.utils.functional import cached_property
from thriftpool.utils.socket import Socket
import logging
import zmq

__all__ = ['Service']

logger = logging.getLogger(__name__)


class BaseService(Base):

    def __init__(self, ident):
        self.ident = ident
        self.reply_to = None
        super(BaseService, self).__init__()

    @cached_property
    def socket(self):
        return Socket(self.app.hub, self.app.ctx, zmq.DEALER)

    def initialize(self):
        self.socket.connect(self.app.config.BROKER_ENDPOINT)
        self.send(self.WorkerCommands.READY)

    def destruct(self):
        self.send(self.WorkerCommands.DISCONNECT)
        self.socket.close()

    def send(self, command, msg=None):
        """Send message to broker. If no message is provided, creates one
        internally.

        """
        message = ['', self.EndpointType.WORKER, self.ident, command]
        message.extend(msg or [])
        self.socket.send_multipart(message)

    def read_request(self):
        message = self.socket.recv_multipart()
        # Don't try to handle errors, just assert noisily
        assert len(message) >= 3, 'wrong message length'
        assert message.pop(0) == '', 'second frame must be empty'
        assert message.pop(0) == self.EndpointType.WORKER, 'wrong endpoint type'

        command = message.pop(0)

        if command == self.WorkerCommands.REQUEST:
            # We should pop and save as many addresses as there are
            # up to a null part, but for now, just save one...
            self.reply_to = message.pop(0)

            assert message.pop(0) == '', 'frame must be empty'

            # We have a request to process
            return self.decode(message.pop(0))

        else:
            raise UnknownCommand()

    def send_reply(self, result):
        self.send(self.WorkerCommands.REPLY, [self.reply_to, '', self.encode(result)])


class Service(BaseService):

    def __init__(self, ident, handler):
        self.handler = handler
        super(Service, self).__init__(ident)

    def loop(self):
        request = self.read_request()

        try:
            method = getattr(self.handler, request['method'])
            args, kwargs = request.get('args', []), request.get('kwargs', {})
            result = method(*args, **kwargs)
            response = {'result': result}
        except Exception as exc:
            logger.exception(exc)
            response = {'exc': exc}

        self.send_reply(response)
