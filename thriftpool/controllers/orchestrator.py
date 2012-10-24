from __future__ import absolute_import

from logging import getLogger

from thriftpool.components.base import Namespace
from thriftpool.controllers.base import Controller

__all__ = ['OrchestratorController']

logger = getLogger(__name__)


class OrchestratorNamespace(Namespace):

    name = 'orchestrator'

    def modules(self):
        return ['thriftpool.components.event_loop',
                'thriftpool.components.listener_pool',
                'thriftpool.components.processor']


class OrchestratorController(Controller):

    Namespace = OrchestratorNamespace

    def __init__(self):
        self.listener_pool = self.worker_pool = None
        super(OrchestratorController, self).__init__()

    def on_before_init(self):
        self.app.loader.on_before_init()
        self.app.finalize()
        super(OrchestratorController, self).on_before_init()

    def on_start(self):
        self.app.loader.on_start()
        super(OrchestratorController, self).on_start()

    def on_shutdown(self):
        self.app.loader.on_shutdown()
        super(OrchestratorController, self).on_shutdown()

    def after_start(self):
        # Call hooks.
        self.app.loader.after_start()
        super(OrchestratorController, self).after_start()
