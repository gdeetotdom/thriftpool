"""Execute external commands by this worker."""
from __future__ import absolute_import

import logging

from pyuv import Pipe

from thriftworker.utils.decorators import cached_property
from thriftworker.utils.loop import in_loop
from thriftworker.utils.mixin import LoopMixin
from thriftpool.components.base import StartStopComponent
from thriftpool.components.proto import Consumer
from thriftpool.utils.mixin import LogsMixin

logger = logging.getLogger(__name__)


class Executor(LogsMixin, LoopMixin):
    """Execute commands provided through pipe."""

    def __init__(self, app, controller):
        self.app = app
        self.controller = controller
        super(Executor, self).__init__()

    @cached_property
    def channel(self):
        channel = Pipe(self.loop)
        channel.open(3)
        return channel

    @cached_property
    def consumer(self):
        return Consumer(self.loop, self.channel,
                        handler=self.controller)

    @in_loop
    def start(self):
        self.consumer.start()

    @in_loop
    def stop(self):
        self.consumer.stop()
        self.channel.close()


class ExecutorComponent(StartStopComponent):

    name = 'worker.executor'
    requires = ('services', 'acceptors', 'loop')

    def create(self, parent):
        return Executor(parent.app, parent)
