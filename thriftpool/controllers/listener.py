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
                'thriftpool.components.listener.device',
                'thriftpool.components.listener.pool']


class ListenerController(Controller):

    Namespace = ListenerNamespace

    def __init__(self, frontend_endpoint, backend_endpoint):
        self.pool = None
        self.frontend_endpoint = frontend_endpoint
        self.backend_endpoint = backend_endpoint
        super(ListenerController, self).__init__()

    @cached_property
    def socket_zmq(self):
        return SocketZMQ(debug=self.app.config.DEBUG)

    def listener(self, slot):
        return self.socket_zmq.Listener(
            slot.name,
            (slot.listener.host, slot.listener.port or 0),
            frontend=self.frontend_endpoint,
            backlog=slot.listener.backlog
        )

    def after_start(self):
        for slot in self.app.slots:
            self.pool.register(self.listener(slot))
        super(ListenerController, self).after_start()

    def on_shutdown(self):
        self.socket_zmq.context.term()
        super(ListenerController, self).on_shutdown()
