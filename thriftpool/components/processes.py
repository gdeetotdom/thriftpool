"""Manage process pool."""
from __future__ import absolute_import

import logging
import sys
import struct
import cPickle as pickle

from pyuv import Pipe

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
        if self.channel is not None and self.channel.active:
            self.channel.stop()


class ProcessManager(LogsMixin, LoopMixin):
    """Start and manage workers."""

    process_name = 'worker'
    name_template = '[thriftworker-{0}]' \
                    ' -c {1.CONCURRENCY}' \
                    ' -k {1.WORKER_TYPE}'
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
                    custom_streams=['handshake', 'incoming', 'outgoing'],
                    custom_channels=self.listeners.channels,
                    redirect_input=True)

    @cached_property
    def _is_stopped(self):
        return self.app.env.RealEvent()

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

    def _bootstrap_process(self, process):
        # Now we can create producer.
        producer = self._create_producer(process)
        # Create name for process.
        create_name = (lambda: self.name_template
                       .format(process.id, self.app.config))
        # Notify about process initialization.
        bootstrap_done = (lambda producer, reply:
                          self._info('Worker %d started!', process.id))
        # And bootstrap remote process.
        producer.apply('change_title',
                       args=[create_name()])
        use_mutex = self.app.config.WORKERS > 1
        descriptors = {i: (listener.name,
                           listener.accept_mutex if use_mutex else None)
                       for i, listener in self.listeners.enumerated.items()}
        producer.apply('register_acceptors',
                       args=[descriptors],
                       callback=bootstrap_done)

    def _do_handshake(self, process):
        # Pass application to created process.
        stream = process.streams['handshake']
        message = pickle.dumps(self.app)
        stream.write(struct.pack('I', len(message)) + message)

        def handshake_done(evtype, info):
            stream.unsubscribe(handshake_done)
            # Process exited and we do the same.
            if not process.active:
                return
            self._bootstrap_process(process)

        # Wait for worker answer.
        stream.subscribe(handshake_done)

    def _redirect_io(self, process):
        """Redirect stdout & stderr."""
        monitor_io = (lambda evtype, msg:
                      (evtype == 'err' and self._stderr or self._stdout)
                      .write(msg['data']))
        process.monitor_io('.', monitor_io)

    def _on_event(self, evtype, msg):
        if msg['name'] != self.process_name:
            return
        if evtype == 'exit':
            self._info('Worker %d exited with code %d!',
                       msg['pid'], msg['exit_status'])
        elif evtype == 'spawn':
            self._debug('Worker %d spawned!', msg['pid'])
        if not self.controller.is_running:
            return
        if evtype == 'spawn':
            process = self.manager.get_process(msg['pid'])
            self._redirect_io(process)
            self._do_handshake(process)
        elif evtype == 'exit':
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
    def _pre_stop(self):
        for producer in self.producers.values():
            producer.stop()
        self.producers = {}
        stop_callback = lambda *args: self._is_stopped.set()
        self.manager.stop(stop_callback)

    @in_loop
    def _post_stop(self):
        self._stderr.close()
        self._stdout.close()

    def stop(self):
        self._pre_stop()
        self._is_stopped.wait(30.0)
        if not self._is_stopped.is_set():
            logger.error('Timeout when stopping processes.')
        self._post_stop()

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
