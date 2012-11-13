"""Manage process pool."""
from __future__ import absolute_import

import logging
import sys
import struct
import cPickle as pickle

from thriftworker.utils.loop import in_loop
from thriftworker.utils.mixin import LoopMixin
from thriftpool.utils.mixin import LogsMixin

from .base import StartStopComponent
from .proto import Producer

logger = logging.getLogger(__name__)


class Workers(LogsMixin, LoopMixin):

    process_name = 'worker'
    script = 'from thriftpool.bin.thriftworker import main; main()'

    def __init__(self, app, manager, listeners):
        self.app = app
        self.manager = manager
        self.listeners = listeners
        self.producers = {}

    def create_arguments(self):
        return dict(cmd=sys.executable,
                    args=['-c', '{0}'.format(self.script)],
                    redirect_output=['out', 'err'],
                    custom_streams=['control'],
                    channels=self.listeners.channels,
                    redirect_input=True)

    def create_producer(self, process):
        channel = process.streams['control'].channel
        producer = self.producers[process.id] = Producer(self.loop, channel, process)
        producer.start()
        return producer

    def _on_io(self, evtype, msg):
        stream = evtype == 'err' and sys.stderr or sys.stdout
        stream.write(msg['data'])

    def initialize_process(self, process):
        process.monitor_io('.', self._on_io)
        message = pickle.dumps(self.app)
        message = struct.pack('I', len(message)) + message
        process.write(message)
        producer = self.create_producer(process)
        producer.apply('ping')
        producer.apply('change_title', args=['[thriftworker-{0}]'.format(process.id)])
        producer.apply('register_acceptors', args=[self.listeners.descriptors])

    @in_loop
    def start(self):
        manager = self.manager
        manager.add_process(self.process_name,
                            numprocesses=self.app.config.WORKERS_COUNT,
                            **self.create_arguments())
        state = manager.get_process_state(self.process_name)
        for process in state.list_processes():
            self.initialize_process(process)
        manager.start()

    @in_loop
    def stop(self):
        for producer in self.producers.values():
            producer.stop()
        self.producers = {}
        self.manager.stop()


class WorkersComponent(StartStopComponent):

    name = 'manager.workers'
    requires = ('loop', 'listeners')

    def create(self, parent):
        workers = parent.workers = Workers(parent.app, parent.manager,
                                           parent.listeners)
        return workers
