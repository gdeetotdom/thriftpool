from __future__ import absolute_import
from thriftpool.rpc import Hub as BaseHub
from thriftpool.worker.abstract import StartStopComponent
from thriftpool.utils.threads import DaemonThread

__all__ = ['BrokerComponent']


class BrokerComponent(StartStopComponent):
    name = 'worker.broker'

    def __init__(self, parent, **kwargs):
        parent.hub_container = None
        super(BrokerComponent, self).__init__(parent, **kwargs)

    def create(self, parent):
        hub_container = parent.hub_container = HubContainer('tcp://*:5556')
        return hub_container


class Hub(BaseHub):
    pass


class HubContainer(DaemonThread):

    Hub = Hub

    def __init__(self, endpoint):
        super(HubContainer, self).__init__()
        self.endpoint = endpoint
        self.hub = self.Hub(self.endpoint)
        self.broker = self.hub.broker()
        self.worker = self.hub.worker('ident')
        self.client = self.hub.client('ident')

    def body(self):
        self.hub.start()

    def stop(self):
        if self.hub is not None:
            self.hub.stop()
        super(HubContainer, self).stop()
