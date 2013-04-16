from __future__ import absolute_import

from logging import getLogger

from thriftpool.components.base import Namespace
from thriftpool.controllers.base import Controller

logger = getLogger(__name__)


class ManagerNamespace(Namespace):

    name = 'manager'

    def modules(self):
        return [
            'thriftpool.components.manager.loop',
            'thriftpool.components.manager.gaffer',
            'thriftpool.components.manager.listeners',
            'thriftpool.components.manager.processes',
            'thriftpool.components.manager.acceptors',
            'thriftpool.components.manager.reaper',
            'thriftpool.components.manager.tornado',
        ]


class ManagerController(Controller):

    Namespace = ManagerNamespace

    listeners = None
    processes = None
