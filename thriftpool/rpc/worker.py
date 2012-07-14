from .base import Greenlet, Socket, JsonProtocol, WorkerCommands, EndpointType
import logging
import zmq

logger = logging.getLogger(__name__)


class BaseWorker(Greenlet, Socket, JsonProtocol):

    hub = None

    def __init__(self, ident):
        self.ident = ident
        super(BaseWorker, self).__init__(self.hub.loop, self.hub.ctx,
                                     self.hub.endpoint, zmq.DEALER)

    def start(self):
        super(BaseWorker, self).start()
        self.register()

    def register(self):
        self.send(WorkerCommands.READY)

    def send(self, command, msg=None):
        """Send message to broker. If no message is provided, creates one
        internally.

        """
        message = ['', EndpointType.WORKER, self.ident, command]
        message.extend(msg or [])
        self.socket.send_multipart(message)

        # trigger zeromq socket
        self.try_receive()

    def receive(self):
        message = self.socket.recv_multipart(zmq.NOBLOCK)
        # Don't try to handle errors, just assert noisily
        assert len(message) >= 3, 'wrong message length'
        assert message.pop(0) == '', 'second frame must be empty'
        assert message.pop(0) == EndpointType.WORKER, 'wrong endpoint type'

        command = message.pop(0)

        if command == WorkerCommands.REQUEST:
            # We should pop and save as many addresses as there are
            # up to a null part, but for now, just save one...
            reply_to = message.pop(0)

            assert message.pop(0) == '', 'frame must be empty'

            # We have a request to process
            result = self.switch(self.decode(message.pop(0)))
            self.switch()
            reply = self.encode(result)
            self.send(WorkerCommands.REPLY, [reply_to, '', reply])

        else:
            logger.error("Invalid input message")

    def run(self):
        raise NotImplementedError("subclass responsibility")


class Worker(BaseWorker):
    pass
