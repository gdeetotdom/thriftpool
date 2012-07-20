from __future__ import absolute_import
from thriftpool.components.base import StartStopComponent
from thriftpool.rpc import Broker


class BrokerComponent(StartStopComponent):

    name = 'orchestrator.broker'
    requires = ('hub', )

    def __init__(self, parent, **kwargs):
        parent.broker = None
        super(BrokerComponent, self).__init__(parent, **kwargs)

    def create(self, parent):
        broker = parent.broker = Broker(parent.app)
        return broker
