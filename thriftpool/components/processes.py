"""Manage process pool."""
from __future__ import absolute_import

import logging
import sys
import struct
import cPickle as pickle

from pyuv import Timer, Pipe

from thriftworker.utils.loop import in_loop
from thriftworker.utils.decorators import cached_property
from thriftworker.utils.mixin import LoopMixin
from thriftpool.utils.mixin import LogsMixin

from .base import StartStopComponent
from .proto import Producer

logger = logging.getLogger(__name__)


class RedirectStream(object):
    """Try to write to stream asynchronous."""

    def __init__(self, loop, stream):
        self.stream = stream
        try:
            fd = stream.fileno()
        except AttributeError:
            self.channel = None
        else:
            channel = self.channel = Pipe(loop)
            channel.open(fd)

    def write(self, data):
        if self.channel is not None:
            self.channel.write(data)
        else:
            self.stream.write(data)

    def close(self):
        if self.channel is not None:
            self.channel.close()


class ProcessManager(LogsMixin, LoopMixin):
    """Start and manage workers."""

    process_name = 'worker'
    gevent_monkey = 'from gevent.monkey import patch_all; patch_all();'
    script = 'from thriftpool.bin.thriftworker import main; main();'

    def __init__(self, app, manager, listeners, controller):
        self.app = app
        self.manager = manager
        self.listeners = listeners
        self.producers = {}
        self.controller = controller
        super(ProcessManager, self).__init__()

    def _create_arguments(self):
        worker_type = self.app.config.WORKER_TYPE
        if worker_type == 'gevent':
            startup_line = '{0} {1}'.format(self.gevent_monkey, self.script)
        elif worker_type == 'sync':
            startup_line = self.script
        else:
            raise NotImplementedError()
        args = ['-c', '{0}'.format(startup_line)]
        return dict(cmd=sys.executable, args=args,
                    redirect_output=['out', 'err'],
                    custom_streams=['incoming', 'outgoing'],
                    custom_channels=self.listeners.channels,
                    redirect_input=True)

    @cached_property
    def _stdout(self):
        return RedirectStream(self.loop, sys.stdout)

    @cached_property
    def _stderr(self):
        return RedirectStream(self.loop, sys.stderr)

    def _create_producer(self, process):
        incoming = process.streams['incoming']
        outgoing = process.streams['outgoing']
        producer = self.producers[process.id] = Producer(self.loop, incoming, outgoing, process)
        producer.start()
        return producer

    def _initialize_process(self, process):
        timers = []

        def on_io(evtype, msg):
            (evtype == 'err' and self._stderr or self._stdout).write(msg['data'])

        def create_producer():
            incoming = process.streams['incoming']
            outgoing = process.streams['outgoing']
            producer = self.producers[process.id] = Producer(self.loop, incoming, outgoing, process)
            producer.start()
            return producer

        def when_done(producer, reply):
            self._info('Process %d initialized!', process.id)

        def bootstrap_process(handle):
            handle.close()
            timers.remove(handle)
            # Process exited
            if not process.active:
                return
            # Now we can create producer
            producer = create_producer()
            producer.apply('change_title',
                           args=['[thriftworker-{0}]'.format(process.id)])
            producer.apply('register_acceptors',
                           args=[self.listeners.descriptors],
                           callback=when_done)

        # Redirect stdout & stderr.
        process.monitor_io('.', on_io)
        # Pass application to created process.
        message = pickle.dumps(self.app)
        message = struct.pack('I', len(message)) + message
        process.write(message)
        # Bootstrap process after some delay.
        timer = Timer(self.loop)
        timers.append(timer)
        timer.start(bootstrap_process, 1, 0)

    def _on_event(self, evtype, msg):
        if msg['name'] != self.process_name:
            return
        if not self.controller.is_running:
            return
        if evtype == 'spawn':
            self._info('Process %d spawned!', msg['pid'])
            process = self.manager.get_process(msg['pid'])
            self._initialize_process(process)
        elif evtype == 'exit':
            self._critical('Process %d exited!', msg['pid'])
            producer = self.producers.pop(msg['pid'], None)
            producer.stop()

    @in_loop
    def start(self):
        manager = self.manager
        manager.subscribe('.', self._on_event)
        manager.add_process(self.process_name,
                            numprocesses=self.app.config.WORKERS,
                            **self._create_arguments())
        manager.start()

    @in_loop
    def _stop(self):
        is_stopped = self.app.env.RealEvent()
        for producer in self.producers.values():
            producer.stop()
        self.producers = {}
        stop_callback = lambda *args: is_stopped.set()
        self.manager.stop(stop_callback)
        self._stderr.close()
        self._stdout.close()
        return is_stopped

    def stop(self):
        is_stopped = self._stop()
        is_stopped.wait(5.0)
        if not is_stopped.is_set():
            logger.error('Timeout when stopping processes.')

    def apply(self, method_name, callback=None, args=None, kwargs=None):
        """Run given method across all processes."""
        for producer in self.producers.values():
            producer.apply(method_name, callback, args, kwargs)


class ProcessManagerComponent(StartStopComponent):

    name = 'manager.process_manager'
    requires = ('loop', 'listeners')

    def create(self, parent):
        return ProcessManager(parent.app, parent.manager,
                              parent.listeners, parent)
