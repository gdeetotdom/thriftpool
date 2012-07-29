from __future__ import absolute_import
from thriftpool.components.base import StartStopComponent


class Mediator(object):

    def __init__(self, app, broker):
        self.pool = {}
        self.app = app
        self.broker = broker
        self.worker_registred = self.broker.worker_registred
        self.worker_deleted = self.broker.worker_deleted

    def start(self):
        self.worker_registred.connect(self.on_new_worker)
        self.worker_deleted.connect(self.on_deleted_worker)

    def stop(self):
        self.worker_registred.disconnect(self.on_new_worker)
        self.worker_deleted.disconnect(self.on_deleted_worker)

    def on_new_worker(self, sender, ident):
        self.pool[ident] = self.app.RemoteProxy(ident)

    def on_deleted_worker(self, sender, ident):
        del self.pool[ident]


class MediatorComponent(StartStopComponent):

    name = 'orchestrator.mediator'
    requires = ('broker', )

    def __init__(self, parent, **kwargs):
        parent.mediator = None
        super(MediatorComponent, self).__init__(parent, **kwargs)

    def create(self, parent):
        broker = parent.mediator = Mediator(parent.app, parent.broker)
        return broker
