from __future__ import absolute_import

from .base import StartStopComponent


class BaseLoopComponent(StartStopComponent):

    abstract = True

    def create(self, parent):
        return parent.app.thriftworker.hub
