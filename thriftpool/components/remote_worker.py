from __future__ import absolute_import
from thriftpool.components.base import StartStopComponent


class RemoteWorkerComponent(StartStopComponent):

    name = 'worker.remote_worker'

    def create(self, parent):
        return parent.app.MDPWorker(parent.ident, parent.container)
