from __future__ import absolute_import
from thriftpool.components.base import StartStopComponent
from thriftpool.containers.listener import ListenerContainer
from thriftpool.utils.functional import cached_property
from thriftpool.utils.other import mk_temp_path


class Mediator(object):

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

    def register_container(self, container):
        ident = self.pool.create(container)
        waiter = self._starting_workers[ident] = self.hub.Waiter()
        return waiter.get()

    def run(self):
        proxy = self.register_container(ListenerContainer(self.app))
        frontend = ('127.0.0.1', 10051)
        backend = "ipc://{0}".format(mk_temp_path())
        proxy.listen_for(frontend, backend)

    def on_new_worker(self, sender, ident):
        waiter = self._starting_workers.pop(ident, None)
        proxy = self._workers[ident] = self.app.RemoteProxy(ident)
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
