from __future__ import absolute_import

from .base import StartStopComponent


class EventLoopProxy(object):
    """Proxy to :class:`socket_zmq.loop.LoopContainer`.

    We should create all instance as later as possible.

    """

    def __init__(self, app):
        self.app = app

    @property
    def loop_container(self):
        """Get loop container from application."""
        return self.app.socket_zmq.loop_container

    def start(self):
        """Start loop container."""
        self.loop_container.start()

    def stop(self):
        """Stop loop container."""
        self.loop_container.stop()


class EventLoopComponent(StartStopComponent):

    name = 'orchestrator.event_loop'
    requiries = ('worker_pool',)

    def create(self, parent):
        return EventLoopProxy(parent.app)
