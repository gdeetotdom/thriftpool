from __future__ import absolute_import
from thriftpool.components.base import StartStopComponent
from thriftpool.utils.functional import cached_property
from thriftpool.utils.logs import LogsMixin
import logging

__all__ = ['MediatorComponent']

logger = logging.getLogger(__name__)


class Mediator(LogsMixin):

    def __init__(self, app, broker):
        self._workers = {}
        self._starting_workers = {}
        self.app = app
        self.hub = app.hub
        self.broker = broker
        self.worker_registred = self.broker.worker_registred
        self.worker_deleted = self.broker.worker_deleted

    @cached_property
    def greenlet(self):
        return self.hub.Greenlet(run=self.run)

    def start(self):
        self.worker_registred.connect(self.on_new_worker)
        self.worker_deleted.connect(self.on_deleted_worker)
        self.greenlet.start()

    def stop(self):
        self.greenlet.kill()
        self.worker_registred.disconnect(self.on_new_worker)
        self.worker_deleted.disconnect(self.on_deleted_worker)
        self._workers.clear()

    def register(self, ident):
        waiter = self._starting_workers[ident] = self.hub.Waiter()
        return waiter.get()

    def run(self):
        pass

    def on_new_worker(self, sender, ident):
        proxy = self._workers[ident] = self.app.MDPProxy(ident)
        waiter = self._starting_workers.pop(ident, None)
        if waiter is not None:
            waiter.switch(proxy)

    def on_deleted_worker(self, sender, ident):
        self._workers.pop(ident)


class MediatorComponent(StartStopComponent):

    name = 'orchestrator.mediator'
    requires = ('broker', 'pool', 'supervisor')

    def __init__(self, parent, **kwargs):
        parent.mediator = None
        super(MediatorComponent, self).__init__(parent, **kwargs)

    def create(self, parent):
        broker = parent.mediator = Mediator(parent.app, parent.broker)
        return broker
