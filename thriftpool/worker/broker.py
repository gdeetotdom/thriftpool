from __future__ import absolute_import
from thriftpool.worker.abstract import StartStopComponent

__all__ = ['BrokerComponent']


class BrokerComponent(StartStopComponent):

    name = 'worker.broker'
    requires = ('hub',)

    def __init__(self, parent, **kwargs):
        parent.broker = None
        super(BrokerComponent, self).__init__(parent, **kwargs)

    def create(self, parent):
        broker = parent.broker = parent.app.Broker()
        return broker
