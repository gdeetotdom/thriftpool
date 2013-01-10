from __future__ import absolute_import

from thriftpool.app import current_app

from .transport import Producer
from .client import Client


class Clients(object):
    """Manage clients."""

    Producer = Producer
    Client = Client

    def __init__(self):
        self._producers = {}
        self._clients = {}
        super(Clients, self).__init__()

    def register(self, process, callback=None, **kwargs):
        """Create new producer for given process."""
        incoming = process.streams['incoming']
        outgoing = process.streams['outgoing']
        producer = self._producers[process.id] = \
            self.Producer(current_app.loop, incoming, outgoing)
        producer.start()
        client = self._clients[process.id] = self.Client(producer)
        if callback is not None:
            client.spawn(callback, process=process, **kwargs)

    def unregister(self, pid):
        """Stop and remove producer by process id."""
        self._clients.pop(pid, None)
        producer = self._producers.pop(pid, None)
        if producer is not None:
            producer.stop()

    def clear(self):
        """Unregister all clients."""
        for pid in list(self._producers):
            self.unregister(pid)

    def spawn(self, run, *args, **kwargs):
        """Map given function to all clients."""
        for client in self._clients.values():
            client.spawn(run, *args, **kwargs)
