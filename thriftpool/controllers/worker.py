from __future__ import absolute_import

from logging import getLogger

from thriftpool.utils.other import setproctitle
from thriftpool.components.base import Namespace
from thriftpool.controllers.base import Controller

logger = getLogger(__name__)


class WorkerNamespace(Namespace):

    name = 'worker'

    def modules(self):
        return ['thriftpool.components.loop',
                'thriftpool.components.worker',
                'thriftpool.components.broker']


class WorkerController(Controller):

    Namespace = WorkerNamespace

    ignore_interrupt = True
    acceptors = None

    def __init__(self, start_fd):
        self.handshake_fd = start_fd
        self.outgoing_fd = self.handshake_fd + 1
        self.incoming_fd = self.outgoing_fd + 1
        super(WorkerController, self).__init__()

    def change_title(self, name):
        """Change process title."""
        setproctitle(name)

    def register_acceptors(self, descriptors):
        """Register all existed acceptors with given descriptors."""
        acceptors = self.acceptors
        slots = self.app.slots
        delta = self.incoming_fd + 1
        for fd, (name, mutex) in descriptors.items():
            slot = slots[name]
            fd += delta
            acceptors.register(fd, name,
                               backlog=slot.listener.backlog,
                               mutex=mutex)
