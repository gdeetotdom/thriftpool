from __future__ import absolute_import
from logging import getLogger
from socket_zmq.app import SocketZMQ
from thriftpool.components.base import Namespace
from thriftpool.controllers.base import Controller
from thriftpool.utils.functional import cached_property

__all__ = ['ListenerController']

logger = getLogger(__name__)


class ListenerNamespace(Namespace):

    name = 'listener'

    def modules(self):
        return ['thriftpool.components.listener.event_loop',
                'thriftpool.components.listener.pool']


class ListenerController(Controller):

    Namespace = ListenerNamespace

    def __init__(self):
        self.pool = None
        super(ListenerController, self).__init__()

    @cached_property
    def socket_zmq(self):
        return SocketZMQ(debug=self.app.config.DEBUG)

    def after_start(self):
        for slot in self.app.slots:
            listener = self.socket_zmq.Listener(
                (slot.listener.host, slot.listener.port or 0),
                backend=slot.backend, backlog=slot.listener.backlog
            )
            self.pool.register(slot.name, listener)
        super(ListenerController, self).after_start()

    def on_shutdown(self):
        self.socket_zmq.context.destroy()
        super(ListenerController, self).on_shutdown()
