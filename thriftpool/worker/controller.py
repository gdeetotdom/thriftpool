from __future__ import absolute_import
from thriftpool.worker.abstract import Namespace as BaseNamespace
from thriftpool.utils.imports import qualname
from logging import getLogger

__all__ = ['Controller']

logger = getLogger(__name__)


class Namespace(BaseNamespace):
    """This is the boot-step namespace of the :class:`Controller`."""
    name = 'worker'

    def modules(self):
        return []


class Controller(object):

    app = None

    def __init__(self):
        self.components = []
        self.namespace = Namespace(app=self.app).apply(self)

    def start(self):
        for component in self.components:
            logger.debug('Starting %s...', qualname(component))
            if component:
                component.start()
