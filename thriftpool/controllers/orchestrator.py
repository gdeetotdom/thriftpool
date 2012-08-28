from __future__ import absolute_import

from logging import getLogger
import socket

from thriftpool.components.base import Namespace
from thriftpool.controllers.base import Controller
from thriftpool.utils.other import setproctitle

__all__ = ['OrchestratorController']

logger = getLogger(__name__)


class OrchestratorNamespace(Namespace):

    name = 'orchestrator'

    def modules(self):
        return ['thriftpool.components.device',
                'thriftpool.components.event_loop',
                'thriftpool.components.listener_pool',
                'thriftpool.components.worker_pool']


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
        # Set process title.
        setproctitle('[{0}@{1}]'.format('orchestrator', socket.gethostname()))
        # Register all listeners and services.
        for slot in self.app.slots:
            self.listener_pool.register(slot.name, slot.listener.host,
                                        slot.listener.port, slot.listener.backlog)
            self.worker_pool.register(slot.name, slot.service.processor)
        super(OrchestratorController, self).after_start()
