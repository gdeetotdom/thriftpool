from __future__ import absolute_import

from logging import getLogger

from thriftpool.components.base import Namespace
from thriftpool.controllers.base import Controller

logger = getLogger(__name__)


class ManagerNamespace(Namespace):

    name = 'manager'

    def modules(self):
        return ['thriftpool.components.loop',
                'thriftpool.components.listeners',
                'thriftpool.components.processes']


class ManagerController(Controller):

    Namespace = ManagerNamespace

    listeners = None
    processes = None
