from __future__ import absolute_import

import sys
from logging import getLogger

from thriftpool.utils.other import setproctitle
from thriftpool.components.base import Namespace
from thriftpool.controllers.base import Controller

logger = getLogger(__name__)


class WorkerNamespace(Namespace):

    name = 'worker'

    def modules(self):
        return ['thriftpool.components.loop',
                'thriftpool.components.signals',
                'thriftpool.components.services',
                'thriftpool.components.worker',
                'thriftpool.components.acceptors',
                'thriftpool.components.broker']


class WorkerController(Controller):

    Namespace = WorkerNamespace

    acceptors = None

    def __init__(self, start_fd=None):
        self.outgoing_fd = start_fd or (sys.stderr.fileno() + 1)
        self.incoming_fd = self.outgoing_fd + 1
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
        self.app.loader.after_start()
        super(WorkerController, self).after_start()

    def ping(self):
        """Ping-pong. Return unique process identification."""
        return self.ident

    def change_title(self, name):
        """Change process title."""
        setproctitle(name)

    def register_acceptors(self, descriptors):
        """Register all existed acceptors with given descriptors."""
        acceptors = self.acceptors
        for descriptor, name in descriptors.items():
            descriptor += self.incoming_fd + 1
            acceptors.add_acceptor(descriptor, name)
