from __future__ import absolute_import

from logging import getLogger

from thriftpool.components.base import Namespace
from thriftpool.controllers.base import Controller

logger = getLogger(__name__)


class WorkerNamespace(Namespace):

    name = 'worker'

    def modules(self):
        return ['thriftpool.components.loop',
                'thriftpool.components.listeners',
                'thriftpool.components.services']


class WorkerController(Controller):

    Namespace = WorkerNamespace

    def __init__(self):
        super(WorkerController, self).__init__()

    def on_before_init(self):
        self.app.loader.on_before_init()
        self.app.finalize()
        super(WorkerController, self).on_before_init()

    def on_start(self):
        self.app.loader.on_start()
        super(WorkerController, self).on_start()

    def on_shutdown(self):
        self.app.loader.on_shutdown()
        super(WorkerController, self).on_shutdown()

    def after_start(self):
        # Call hooks.
        self.app.loader.after_start()
        super(WorkerController, self).after_start()
