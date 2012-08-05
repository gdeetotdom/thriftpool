from __future__ import absolute_import
from thriftpool.cartridges.listener import ListenerCartridge
from thriftpool.components.base import StartStopComponent
from thriftpool.utils.functional import cached_property
from thriftpool.utils.logs import LogsMixin
from thriftpool.utils.other import mk_temp_path
import logging
from thriftpool.cartridges.worker import WorkerCartridge

__all__ = ['MediatorComponent']

logger = logging.getLogger(__name__)


class Mediator(LogsMixin):

    def __init__(self, app, broker, pool):
        self._workers = {}
        self._starting_workers = {}
        self.app = app
        self.hub = app.hub
        self.broker = broker
        self.pool = pool
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

    def register_cartridge(self, cartridge):
        ident = self.pool.create(cartridge)
        self._debug('Initiate cartridge "%s"', type(cartridge).__name__)
        waiter = self._starting_workers[ident] = self.hub.Waiter()
        return waiter.get()

    def run(self):
        listener_proxy = self.register_cartridge(ListenerCartridge(self.app))
        frontend = ('127.0.0.1', 10051)
        backend = "ipc://{0}".format(mk_temp_path())
        listener_proxy.listen_for(frontend, backend)

        worker_proxy = self.register_cartridge(WorkerCartridge(self.app))
        worker_proxy.handle(backend)

    def on_new_worker(self, sender, ident):
        waiter = self._starting_workers.pop(ident, None)
        proxy = self._workers[ident] = self.app.MDPProxy(ident)
        if waiter is not None:
            waiter.switch(proxy)

    def on_deleted_worker(self, sender, ident):
        del self._workers[ident]


class MediatorComponent(StartStopComponent):

    name = 'orchestrator.mediator'
    requires = ('broker', 'pool', 'supervisor')

    def __init__(self, parent, **kwargs):
        parent.mediator = None
        super(MediatorComponent, self).__init__(parent, **kwargs)

    def create(self, parent):
        broker = parent.mediator = Mediator(parent.app, parent.broker, parent.pool)
        return broker
