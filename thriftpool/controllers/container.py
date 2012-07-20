from __future__ import absolute_import
from logging import getLogger
from thriftpool.components.base import Namespace as BaseNamespace
from thriftpool.controllers.base import Controller

logger = getLogger(__name__)


class Namespace(BaseNamespace):

    name = 'container'

    def modules(self):
        return ['thriftpool.components.hub',
                'thriftpool.components.container']


class Container(Controller):

    Namespace = Namespace
