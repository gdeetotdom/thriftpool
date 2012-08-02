from __future__ import absolute_import
from socket_zmq.utils import in_loop
from thriftpool.components.base import StartStopComponent
from thriftpool.utils.threads import SimpleDaemonThread

__all__ = ['ListenerLoopComponent']


class LoopContainer(object):
    """Run event loop in separate thread."""

    def __init__(self, loop):
        self.loop = loop
        self.thread = SimpleDaemonThread(target=self.loop.start)

    def start(self):
        self.thread.start()

    @in_loop
    def _shutdown(self):
        self.loop.stop()

    def stop(self):
        self._shutdown()
        self.thread.stop()


class ListenerLoopComponent(StartStopComponent):

    name = 'listener.listener_loop'

    def create(self, parent):
        return LoopContainer(parent.socket_zmq.loop)
