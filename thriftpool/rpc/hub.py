from greenlet import greenlet
from thriftpool.utils.functional import cached_property
from thriftpool.utils.mixin import SubclassMixin
import pyev
import zmq


class Hub(SubclassMixin):

    #: Describe which class should used as broker.
    broker_cls = 'thriftpool.rpc.broker:Broker'

    #: Describe which class should used as worker.
    worker_cls = 'thriftpool.rpc.worker:Worker'

    #: Describe which class should used as client.
    client_cls = 'thriftpool.rpc.client:Client'

    def __init__(self, endpoint):
        self.loop = pyev.Loop(debug=True)
        self.ctx = zmq.Context()
        self.endpoint = endpoint
        self.watchers = []
        self._async = pyev.Async(self.loop, self._shutdown)
        self._async.start()
        super(Hub, self).__init__()

    @cached_property
    def greenlet(self):
        return greenlet(run=self.run)

    @cached_property
    def Broker(self):
        return self.subclass_with_self(self.broker_cls, attribute='hub')

    @cached_property
    def Worker(self):
        return self.subclass_with_self(self.worker_cls, attribute='hub')

    @cached_property
    def Client(self):
        return self.subclass_with_self(self.client_cls, attribute='hub')

    def register(self, watcher):
        self.watchers.append(watcher)
        return watcher

    def start(self):
        self.greenlet.switch()

    def run(self):
        for watcher in self.watchers:
            watcher.start()
        self.loop.start()

    def stop(self):
        # we should run shutdown method in same thread as loop's thread
        self._async.send()

    def _shutdown(self, watcher, revents):
        self.loop.stop()
        for watcher in self.watchers:
            watcher.close()

    def broker(self):
        return self.register(self.Broker())

    def client(self, ident):
        return self.register(self.Client(ident))

    def worker(self, ident):
        return self.register(self.Worker(ident))
