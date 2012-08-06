from .base import Base
from collections import namedtuple
from thriftpool.utils.dispatcher import Signal
from thriftpool.utils.functional import cached_property
from thriftpool.utils.logs import LogsMixin
from thriftpool.utils.socket import Socket
import logging
import zmq

logger = logging.getLogger(__name__)


class ServiceEntity(namedtuple('WorkerEntity', 'address')):
    """Some information about registered service."""


class ServiceRepository(LogsMixin):
    """Contains all registered workers. Provide methods to work with this set.

    """

    Entity = ServiceEntity

    def __init__(self, hub, worker_registred, worker_deleted):
        self.workers = {}
        self.hub = hub
        self.worker_registred = worker_registred
        self.worker_deleted = worker_deleted
        super(ServiceRepository, self).__init__()

    def __getitem__(self, ident):
        """Get the worker."""
        return self.workers[ident]

    def __delitem__(self, ident):
        """Delete the worker."""
        self._debug("Deleting worker: %s", ident)
        try:
            del self.workers[ident]
            self.hub.Greenlet(self.worker_deleted.send, sender=self, ident=ident).start()
        except KeyError:
            pass

    def __contains__(self, ident):
        """Check if worker's address already exists."""
        return ident in self.workers

    def register(self, ident, address):
        """Create new service. Return it if exists."""
        try:
            worker = self.workers[ident]
        except KeyError:
            self._debug("Registering new worker: %s", ident)
            worker = self.workers[ident] = self.Entity(address)
            self.hub.Greenlet(self.worker_registred.send, sender=self, ident=ident).start()
        return worker


class Broker(Base, LogsMixin):
    """Pass messages between workers and clients. Messages routed by worker
    identification.

    """

    def __init__(self):
        # called when registered worker was deleted.
        self.worker_deleted = Signal()
        # called when new worker registered.
        self.worker_registred = Signal()
        # create new repository
        self.repo = ServiceRepository(self.app.hub,
                                      self.worker_registred,
                                      self.worker_deleted)
        super(Broker, self).__init__()

    @cached_property
    def socket(self):
        return Socket(self.app.hub, self.app.context, zmq.ROUTER)

    def initialize(self):
        self.socket.bind(self.app.config.BROKER_ENDPOINT)

    def destruct(self):
        self.socket.close()

    def loop(self):
        message = self.socket.recv_multipart()
        sender = message.pop(0)
        assert message.pop(0) == '', 'wait empty frame'
        header = message.pop(0)

        if (header == self.EndpointType.CLIENT):
            self.process_client(sender, message)

        elif (header == self.EndpointType.WORKER):
            self.process_worker(sender, message)

        else:
            self._error('Invalid message')

    def process_client(self, sender, message):
        """Process request coming from client."""
        assert len(message) >= 2, "require worker name and body"

        ident = message.pop(0)
        assert message.pop(0) == self.ClientCommands.REQUEST, 'not request'

        if ident in self.repo:
            worker = self.repo[ident]
            # Send request with return address of client
            message = [worker.address, '', self.EndpointType.WORKER,
                       self.WorkerCommands.REQUEST, sender, ''] + message

        else:
            message = [sender, '', self.EndpointType.CLIENT, ident,
                       self.ClientCommands.NOTFOUND] + message

        self.socket.send_multipart(message)

    def process_worker(self, sender, message):
        """Process response, coming from worker."""
        assert len(message) >= 2, "require, at least, command"

        ident = message.pop(0)
        command = message.pop(0)
        ready = ident in self.repo

        if command == self.WorkerCommands.READY:
            if ready:
                del self.repo[ident]
            else:
                self.repo.register(ident, sender)

        elif command == self.WorkerCommands.REPLY:
            assert ready, 'worker not ready'

            # Remove & save client return envelope and insert the
            # protocol header, then re-wrap envelope.
            client = message.pop(0)
            assert message.pop(0) == '', 'wait empty message'

            message = [client, '', self.EndpointType.CLIENT, ident,
                       self.ClientCommands.REPLY] + message
            self.socket.send_multipart(message)

        elif command == self.WorkerCommands.DISCONNECT:
            del self.repo[ident]

        else:
            self._error('Invalid message')
