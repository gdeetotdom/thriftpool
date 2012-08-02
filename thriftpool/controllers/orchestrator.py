from __future__ import absolute_import
from logging import getLogger
from thriftpool.components.base import Namespace
from thriftpool.controllers.base import Controller

__all__ = ['OrchestratorController']

logger = getLogger(__name__)


class OrchestratorNamespace(Namespace):

    name = 'orchestrator'

    def modules(self):
        return ['thriftpool.components.broker',
                'thriftpool.components.pool',
                'thriftpool.components.supervisor',
                'thriftpool.components.mediator']


class OrchestratorController(Controller):

    Namespace = OrchestratorNamespace

    def on_start(self):
        self.app.loader.on_start()

    def on_shutdown(self):
        self.app.loader.on_shutdown()
        self.app.hub.stop()
