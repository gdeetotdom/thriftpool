from __future__ import absolute_import
from logging import getLogger
from thriftpool.components.base import Namespace
from thriftpool.controllers.base import Controller
from thriftpool.utils.other import mk_temp_path
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

    def __init__(self):
        self.pool = None
        self.frontend_endpoint = 'inproc://{0}'.format(id(self))
        self.backend_endpoint = 'ipc://{0}'.format(mk_temp_path(prefix='slot'))
        super(OrchestratorController, self).__init__()

    def on_before_init(self):
        self.app.loader.on_before_init()
        self.app.finalize()
        super(OrchestratorController, self).on_before_init()

    def on_start(self):
        setproctitle('[{0}]'.format('Orchestrator'))
        self.app.loader.on_start()
        super(OrchestratorController, self).on_start()

    def on_shutdown(self):
        self.app.loader.on_shutdown()
        super(OrchestratorController, self).on_shutdown()

    def after_start(self):
        self.pool.register(self.app.ListenerController(self.frontend_endpoint,
                                                       self.backend_endpoint))
        for i in xrange(2):
            self.pool.register(self.app.WorkerController(self.backend_endpoint))
        super(OrchestratorController, self).after_start()

