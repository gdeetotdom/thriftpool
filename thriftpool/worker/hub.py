from __future__ import absolute_import
from thriftpool.utils.threads import DaemonThread
from thriftpool.worker.abstract import StartStopComponent

__all__ = ['HubComponent']


class HubComponent(StartStopComponent):
    name = 'worker.hub'

    def create(self, parent):
        return HubThread(parent.app.hub)


class HubThread(DaemonThread):

    def __init__(self, hub):
        super(HubThread, self).__init__()
        self.hub = hub

    def body(self):
        self.hub.start()

    def stop(self):
        self.hub.stop()
        super(HubThread, self).stop()
