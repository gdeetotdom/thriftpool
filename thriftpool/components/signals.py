from __future__ import absolute_import

from pyuv import Signal

from .base import StartStopComponent

from thriftworker.utils.loop import in_loop
from thriftworker.utils.decorators import cached_property
from thriftworker.utils.mixin import LoopMixin


class Signals(LoopMixin):

    def __init__(self, app, controller):
        self.app = app
        self.controller = controller

    @cached_property
    def _handler(self):
        return Signal(self.loop)

    @in_loop
    def start(self):
        self._handler.start()

    @in_loop
    def stop(self):
        if self._handler.active:
            self._handler.stop()
            self._handler.close()


class BaseSignalComponent(StartStopComponent):

    abstract = True

    def create(self, parent):
        return Signals(parent.app, parent)


class WorkerSignalComponent(BaseSignalComponent):

    name = 'worker.signals'
    requires = ('loop',)


class ManagerSignalComponent(BaseSignalComponent):

    name = 'manager.signals'
    requires = ('loop',)
