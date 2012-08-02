from __future__ import absolute_import
from thriftpool.components.base import StartStopComponent


class BrokerComponent(StartStopComponent):

    name = 'orchestrator.broker'

    def __init__(self, parent, **kwargs):
        parent.broker = None
        super(BrokerComponent, self).__init__(parent, **kwargs)

    def create(self, parent):
        broker = parent.broker = parent.app.MDPBroker()
        return broker
