from .base import Container
from socket_zmq.app import SocketZMQ
from thriftpool.utils.functional import cached_property
from thriftpool.utils.threads import SimpleDaemonThread

__all__ = ['ListenerContainer']


class ListenerContainer(Container):

    def __init__(self, app):
        self.app = app

    @cached_property
    def _socket_zmq(self):
        return SocketZMQ(debug=self.app.config.DEBUG)

    @cached_property
    def _thread(self):
        return SimpleDaemonThread(target=self._socket_zmq.controller.start)

    def on_start(self):
        self._thread.start()

    def on_stop(self):
        self._socket_zmq.controller.stop()
        self._thread.stop()

    def listen_for(self, frontend, backend):
        socket_zmq = self._socket_zmq
        controller = socket_zmq.controller
        component = socket_zmq.ProxyComponent(frontend, backend)
        controller.register(component)
