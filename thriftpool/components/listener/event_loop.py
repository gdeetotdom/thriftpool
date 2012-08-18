from __future__ import absolute_import
from socket_zmq.utils import in_loop
from thriftpool.components.base import StartStopComponent
from thriftpool.utils.threads import SimpleDaemonThread

__all__ = ['EventLoopContainer']


class EventLoopContainer(object):
    """Run event loop in separate thread."""

    def __init__(self, loop):
        self.loop = loop
        self._on_stop = self.loop.async(lambda *args: None)
        self._on_stop.start()
        self.thread = SimpleDaemonThread(target=self.run,
                                         name='EventLoop')

    def start(self):
        self.thread.start()

    def run(self):
        self.loop.start()

    @in_loop
    def _shutdown(self):
        self._on_stop.stop()
        self.loop.stop()

    def stop(self):
        self._shutdown()
        self.thread.stop()


class EventLoopComponent(StartStopComponent):

    name = 'listener.event_loop'

    def create(self, parent):
        return EventLoopContainer(parent.socket_zmq.loop)
