from __future__ import absolute_import

import logging

from thriftpool.components.base import StartStopComponent

logger = logging.getLogger(__name__)


class WorkerComponent(StartStopComponent):

    name = 'worker.worker'
    requires = ('loop', 'services')

    def create(self, parent):
        return parent.app.thriftworker.worker
