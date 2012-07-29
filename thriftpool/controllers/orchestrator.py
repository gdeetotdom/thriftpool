from __future__ import absolute_import
from logging import getLogger
from thriftpool.components.base import Namespace as BaseNamespace
from thriftpool.controllers.base import Controller

logger = getLogger(__name__)


class Namespace(BaseNamespace):

    name = 'orchestrator'

    def modules(self):
        return ['thriftpool.components.broker',
                'thriftpool.components.pool',
                'thriftpool.components.supervisor',
                'thriftpool.components.mediator']


class Orchestrator(Controller):

    Namespace = Namespace
