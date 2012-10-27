from __future__ import absolute_import

from .base import StartStopComponent


class LoopComponent(StartStopComponent):

    name = 'worker.loop'

    def create(self, parent):
        return parent.app.thriftworker.loop_container
