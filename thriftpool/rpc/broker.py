from .base import Socket, ClientCommands, WorkerCommands, EndpointType
import logging
import zmq

logger = logging.getLogger(__name__)


class WorkerEntity(object):

    def __init__(self, address):
        self.address = address


class WorkerRepository(object):

    def __init__(self):
        self.workers = {}

    def __getitem__(self, ident):
        """Get the worker."""
        return self.workers[ident]

    def __delitem__(self, ident):
        """Delete the worker."""
        del self.workers[ident]

    def __contains__(self, ident):
        """Check if worker's address already exists."""
        return ident in self.workers

    def register(self, ident, address):
        """Create new service. Return it if exists."""
        try:
            worker = self.workers[ident]
        except KeyError:
            logger.info("Registering new worker: %s", ident)
            worker = self.workers[ident] = WorkerEntity(address)
        return worker


class Broker(Socket):

    hub = None

    def __init__(self):
        self.workers = WorkerRepository()
        super(Broker, self).__init__(self.hub.loop, self.hub.ctx,
                                     self.hub.endpoint, zmq.ROUTER)

    def start(self):
        self.watcher.start()
        self.socket.bind(self.endpoint)

    def receive(self):
        message = self.socket.recv_multipart(zmq.NOBLOCK)
        sender = message.pop(0)
        assert message.pop(0) == '', 'wait empty frame'
        header = message.pop(0)

        if (header == EndpointType.CLIENT):
            self.process_client(sender, message)

        elif (header == EndpointType.WORKER):
            self.process_worker(sender, message)

        else:
            logger.error('Invalid message')

    def process_client(self, sender, message):
        """Process request coming from client."""
        assert len(message) >= 2, "require worker name and body"

        ident = message.pop(0)
        assert message.pop(0) == ClientCommands.REQUEST, 'not request'

        if ident in self.workers:
            worker = self.workers[ident]
            # Send request with return address of client
            message = [worker.address, '', EndpointType.WORKER,
                       WorkerCommands.REQUEST, sender, ''] + message

        else:
            message = [sender, '', EndpointType.CLIENT, ident,
                       ClientCommands.NOTFOUND] + message

        self.socket.send_multipart(message)

    def process_worker(self, sender, message):
        """Process response, coming from worker."""
        assert len(message) >= 2, "require, at least, command"

        ident = message.pop(0)
        command = message.pop(0)
        ready = ident in self.workers

        if command == WorkerCommands.READY:
            if ready:
                del self.workers[ident]
            else:
                self.workers.register(ident, sender)

        elif command == WorkerCommands.REPLY:
            assert ready, 'worker not ready'

            # Remove & save client return envelope and insert the
            # protocol header, then re-wrap envelope.
            client = message.pop(0)
            assert message.pop(0) == '', 'wait empty message'

            message = [client, '', EndpointType.CLIENT, ident,
                       ClientCommands.REPLY] + message
            self.socket.send_multipart(message)

        elif command == WorkerCommands.DISCONNECT:
            del self.workers[ident]

        else:
            logger.error('Invalid message')
