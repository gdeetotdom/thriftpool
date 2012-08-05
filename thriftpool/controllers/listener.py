from __future__ import absolute_import
from logging import getLogger
from thriftpool.components.base import Namespace
from thriftpool.controllers.base import NestedController

__all__ = ['ListenerController']

logger = getLogger(__name__)


class ListenerNamespace(Namespace):

    name = 'listener'

    def modules(self):
        return ['thriftpool.components.listener.event_loop',
                'thriftpool.components.listener.listener_pool']


class ListenerController(NestedController):

    Namespace = ListenerNamespace

    def __init__(self, socket_zmq):
        self.socket_zmq = socket_zmq
        self.pool = None
        super(ListenerController, self).__init__()
