"""Execute external commands by this worker."""
from __future__ import absolute_import

import logging

from pyuv import Pipe
from gaffer.events import EventEmitter

from thriftworker.utils.decorators import cached_property
from thriftworker.utils.loop import in_loop
from thriftworker.utils.mixin import LoopMixin

from thriftpool.components.base import StartStopComponent
from thriftpool.rpc.transport import Consumer
from thriftpool.utils.mixin import LogsMixin

logger = logging.getLogger(__name__)


class Stream(object):
    """Wrapper for plain file descriptor."""

    def __init__(self, loop, fd):
        self.loop = loop
        self.channel = Pipe(loop)
        self.fd = fd
        self._emitter = EventEmitter(loop)

    def start(self):
        self._emitter.subscribe("WRITE", self._on_write)
        self.channel.open(self.fd)
        self.channel.start_read(self._on_read)

    def write(self, data):
        self._emitter.publish("WRITE", data)

    def subscribe(self, listener):
        self._emitter.subscribe('READ', listener)

    def unsubscribe(self, listener):
        self._emitter.unsubscribe('READ', listener)

    def stop(self, all_events=False):
        if self.channel.active:
            self.channel.close()

        if all_events:
            self._emitter.close()

    def _on_write(self, evtype, data):
        self.channel.write(data)

    def _on_read(self, handle, data, error):
        if not data:
            return

        msg = dict(event='READ', data=data)
        self._emitter.publish('READ', msg)


class PerspectiveBroker(LogsMixin, LoopMixin):
    """Execute commands provided through pipe."""

    def __init__(self, app, controller):
        self.app = app
        self.controller = controller
        super(PerspectiveBroker, self).__init__()

    @cached_property
    def handshake_stream(self):
        return Stream(self.loop, self.controller.handshake_fd)

    @cached_property
    def incoming_stream(self):
        return Stream(self.loop, self.controller.incoming_fd)

    @cached_property
    def outgoing_stream(self):
        return Stream(self.loop, self.controller.outgoing_fd)

    @property
    def streams(self):
        return [self.handshake_stream,
                self.incoming_stream,
                self.outgoing_stream]

    @cached_property
    def consumer(self):
        return Consumer(self.loop,
                        incoming=self.incoming_stream,
                        outgoing=self.outgoing_stream,
                        handler=self.controller)

    @in_loop
    def start(self):
        for stream in self.streams:
            stream.start()
        self.handshake_stream.write('x')
        self.consumer.start()

    @in_loop
    def stop(self):
        self.consumer.stop()
        for stream in self.streams:
            stream.stop(all_events=True)


class PerspectiveBrokerComponent(StartStopComponent):

    name = 'worker.broker'
    requires = ('loop', 'acceptors', 'worker')

    def create(self, parent):
        return PerspectiveBroker(parent.app, parent)
