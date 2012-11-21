"""Start acceptors here."""
from __future__ import absolute_import

import logging

from thriftworker.utils.decorators import cached_property
from thriftworker.utils.loop import in_loop
from thriftworker.utils.mixin import LoopMixin
from thriftpool.components.base import StartStopComponent
from thriftpool.utils.mixin import LogsMixin

logger = logging.getLogger(__name__)


class AcceptorsManager(LogsMixin, LoopMixin):

    def __init__(self, app):
        self.app = app
        self.slots = {}

    @cached_property
    def acceptors(self):
        return self.app.thriftworker.Acceptors()

    @cached_property
    def Acceptor(self):
        """Shortcut to :class:`thriftworker.acceptor.Acceptor` class."""
        return self.app.thriftworker.Acceptor

    def register(self, slot):
        self.slots[slot.name] = slot

    def add_acceptor(self, descriptor, name, mutex=None):
        assert name in self.slots, 'wrong name given'
        kwargs = dict(backlog=self.slots[name].listener.backlog,
                      mutex=mutex)
        acceptor = self.Acceptor(name, descriptor, **kwargs)
        self.acceptors.register(acceptor)

    def start(self):
        self.acceptors.start()

    def stop(self):
        self.acceptors.stop()


class AcceptorsComponent(StartStopComponent):

    name = 'worker.acceptors'
    requires = ('loop',)

    def create(self, parent):
        acceptors = parent.acceptors = AcceptorsManager(parent.app)
        for slot in parent.app.slots:
            acceptors.register(slot)
        return acceptors
