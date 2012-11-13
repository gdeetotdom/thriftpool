"""Start acceptors here."""
from __future__ import absolute_import

import logging

from pyuv import Pipe

from thriftworker.utils.decorators import cached_property
from thriftworker.utils.loop import in_loop
from thriftworker.utils.mixin import LoopMixin
from thriftpool.components.base import StartStopComponent
from thriftpool.utils.mixin import LogsMixin

logger = logging.getLogger(__name__)


class Acceptors(LogsMixin, LoopMixin):

    def __init__(self, app):
        self.app = app
        self.slots = {}
        self.acceptors = {}

    @cached_property
    def Acceptor(self):
        """Shortcut to :class:`thriftworker.acceptor.Acceptor` class."""
        return self.app.thriftworker.Acceptor

    def register(self, slot):
        self.slots[slot.name] = slot

    @in_loop
    def add_acceptor(self, descriptor, name):
        assert name in self.slots, 'wrong name given'
        pipe = Pipe(self.loop)
        pipe.open(descriptor)
        kwargs = dict(backlog=self.slots[name].listener.backlog)
        acceptor = self.acceptors[name] = self.Acceptor(name, pipe, **kwargs)
        acceptor.start()

    @in_loop
    def start(self):
        pass

    @in_loop
    def stop(self):
        for acceptor in self.acceptors.values():
            acceptor.stop()
        self.acceptors = {}


class AcceptorsComponent(StartStopComponent):

    name = 'worker.acceptors'
    requires = ('loop',)

    def create(self, parent):
        acceptors = parent.acceptors = Acceptors(parent.app)
        for slot in parent.app.slots:
            acceptors.register(slot)
        return acceptors
