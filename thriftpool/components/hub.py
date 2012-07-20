from __future__ import absolute_import
from thriftpool.app.hub import HubThread
from thriftpool.components.base import StartStopComponent


class BaseHubComponent(StartStopComponent):

    abstract = True

    def create(self, parent):
        return HubThread(parent.app.hub)


class ContainerHubComponent(BaseHubComponent):
    name = 'container.hub'


class OrchestratorHubComponent(BaseHubComponent):
    name = 'orchestrator.hub'
