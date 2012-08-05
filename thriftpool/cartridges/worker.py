from .base import ControllerCartridge
from thriftpool.remote.ThriftPool import Processor, Iface
from thriftpool.utils.logs import LogsMixin
import logging

__all__ = ['WorkerCartridge']

logger = logging.getLogger(__name__)


class Handle(Iface):
    pass


class WorkerCartridge(ControllerCartridge, LogsMixin):

    def create(self):
        return self.app.WorkerController()

    def handle(self, backend):
        processor = Processor(Handle())
        self._info('Registering new worker at "%s".', backend)
        self.controller.pool.register(backend, processor)
