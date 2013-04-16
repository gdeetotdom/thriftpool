from __future__ import absolute_import

from thriftworker.utils.loop import in_loop

from .transport import Producer
from .client import Client


class Broker(object):
    """Used to pass commands to all known slaves."""

    Producer = Producer
    Client = Client

    def __init__(self, app):
        self.app = app
        self._producers = {}
        self._clients = {}
        super(Broker, self).__init__()

    def __iter__(self):
        return iter(self._clients)

    def __getitem__(self, key):
        return self._clients[key]

    def __contains__(self, key):
        return key in self._clients

    def keys(self):
        return self._clients.keys()

    def register(self, process, callback=None, **kwargs):
        """Create new producer for given process."""
        incoming = process.streams['incoming']
        outgoing = process.streams['outgoing']
        producer = self._producers[process.pid] = \
            self.Producer(self.app.loop, incoming, outgoing, process)
        producer.start()
        client = self._clients[process.pid] = self.Client(self.app, producer)
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

    @in_loop
    def spawn(self, run, *args, **kwargs):
        """Map given function to all clients."""
        greenlets = {}
        for key, client in self._clients.items():
            greenlets[key] = client.spawn(run, *args, **kwargs)
        return greenlets
