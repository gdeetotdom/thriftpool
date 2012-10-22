from __future__ import absolute_import

from .base import StartStopComponent


class CollectorProxy(object):

    def __init__(self, app):
        self.app = app

    @property
    def collector(self):
        """Get collector container from application."""
        return self.app.socket_zmq.collector

    def start(self):
        """Start collector container."""
        self.collector.start()

    def stop(self):
        """Stop collector container."""
        self.collector.stop()


class CollectorComponent(StartStopComponent):

    name = 'orchestrator.collector'
    requiries = ('event_loop',)

    def create(self, parent):
        return CollectorProxy(parent.app)
