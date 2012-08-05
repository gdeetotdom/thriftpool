from __future__ import absolute_import
from logging import getLogger
from thriftpool.components.base import Namespace
from thriftpool.controllers.base import Controller
from thriftpool.utils.proctitle import setproctitle

__all__ = ['OrchestratorController']

logger = getLogger(__name__)


class OrchestratorNamespace(Namespace):

    name = 'orchestrator'

    def modules(self):
        return ['thriftpool.components.orchestrator.broker',
                'thriftpool.components.orchestrator.pool',
                'thriftpool.components.orchestrator.supervisor',
                'thriftpool.components.orchestrator.mediator']


class OrchestratorController(Controller):

    Namespace = OrchestratorNamespace

    def on_before_init(self):
        self.app.loader.on_before_init()

    def on_start(self):
        setproctitle('[{0}]'.format('Orchestrator'))
        self.app.loader.on_start()

    def on_shutdown(self):
        self.app.loader.on_shutdown()
        self.app.hub.stop()
