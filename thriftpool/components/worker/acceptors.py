from __future__ import absolute_import

import logging

from thriftpool.components.base import StartStopComponent

logger = logging.getLogger(__name__)


class AcceptorsComponent(StartStopComponent):

    name = 'worker.acceptors'
    requires = ('loop', 'worker')

    def create(self, parent):
        acceptors = parent.acceptors = parent.app.thriftworker.acceptors
        return acceptors
