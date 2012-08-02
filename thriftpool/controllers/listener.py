from __future__ import absolute_import
from logging import getLogger
from thriftpool.components.base import Namespace
from thriftpool.controllers.base import NestedController
from socket_zmq import SocketZMQ

__all__ = ['ListenerController']

logger = getLogger(__name__)


class ListenerNamespace(Namespace):

    name = 'listener'

    def modules(self):
        return ['thriftpool.components.listener_loop']


class ListenerController(NestedController):

    Namespace = ListenerNamespace

    def __init__(self):
        self.socket_zmq = SocketZMQ(debug=self.app.config.DEBUG)
        super(ListenerController, self).__init__()
