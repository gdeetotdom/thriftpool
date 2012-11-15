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


class PerspectiveBroker(LogsMixin, LoopMixin):
    """Execute commands provided through pipe."""

    def __init__(self, app, controller):
        self.app = app
        self.controller = controller
        super(PerspectiveBroker, self).__init__()

    @cached_property
    def channel(self):
        channel = Pipe(self.loop)
        channel.open(self.controller.control_fd)
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


class PerspectiveBrokerComponent(StartStopComponent):

    name = 'worker.broker'
    requires = ('acceptors', 'worker')

    def create(self, parent):
        return PerspectiveBroker(parent.app, parent)
