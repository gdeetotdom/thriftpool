from __future__ import absolute_import

from logging import getLogger

from six import iteritems

from thriftpool.utils.platforms import set_process_title
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

    def on_before_init(self):
        super(WorkerController, self).on_before_init()
        app = self.app
        if app.config.REDIRECT_STDOUT:
            logger = getLogger('thriftpool.stdout')
            app.log.redirect_stdouts_to_logger(logger)

    def change_title(self, name):
        """Change process title."""
        self._debug('Change process title to %r.', name)
        set_process_title(name)

    def register_acceptors(self, descriptors):
        """Register all existed acceptors with given descriptors."""
        acceptors = self.acceptors
        slots = self.app.slots
        delta = self.incoming_fd + 1
        for fd, name in iteritems(descriptors):
            slot = slots[name]
            fd += delta
            self._debug('Register acceptor %r with fd %d.', name, fd)
            acceptors.register(fd, name, backlog=slot.listener.backlog)

    def start_acceptor(self, name):
        """Start acceptors by it's name."""
        self._debug('Start acceptor %r.', name)
        self.acceptors.start_by_name(name)

    def stop_acceptor(self, name):
        """Stop acceptors by it's name."""
        self._debug('Stop acceptor %r.', name)
        self.acceptors.stop_by_name(name)

    def get_counters(self):
        """Return counters here."""
        return self.app.thriftworker.counters.to_dict()

    def get_timers(self):
        """Return timers here."""
        return self.app.thriftworker.timers.to_dict()
