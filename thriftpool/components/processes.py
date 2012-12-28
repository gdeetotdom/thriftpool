"""Manage process pool."""
from __future__ import absolute_import

import logging
import sys
import struct
import cPickle as pickle

from pyuv import Pipe
from six import iteritems

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


class Producers(dict):

    def __getattr__(self, name):

        def inner_function(*args, **kwargs):
            results = []
            for producer in self.values():
                results.append(getattr(producer, name)(*args, **kwargs))
            return results

        inner_function.__name__ = name
        return inner_function


class ProcessManager(LogsMixin, LoopMixin):
    """Start and manage workers."""

    process_name = 'worker'
    name_template = '[thriftworker-{0}]' \
                    ' -c {1.CONCURRENCY}' \
                    ' -k {1.WORKER_TYPE}'
    gevent_monkey = 'from gevent.monkey import patch_all; patch_all();'
    script = 'from thriftpool.bin.thriftworker import main; main();'

    def __init__(self, app, listeners, controller):
        self.app = app
        self.listeners = listeners
        self.producers = Producers()
        self.controller = controller
        self.bootstrapped = {}
        super(ProcessManager, self).__init__()

    @property
    def manager(self):
        return self.app.gaffer_manager

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
    def _is_started(self):
        return self.app.env.RealEvent()

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
        producer = self.producers[process.id] = \
            Producer(self.loop, incoming, outgoing, process)
        producer.start()
        return producer

    def _bootstrap_process(self, process):
        # Now we can create producer.
        producer = self._create_producer(process)

        # Create name for process.
        name = self.name_template.format(process.id, self.app.config)

        # Notify about process initialization.
        def bootstrap_done(producer, reply):
            self.bootstrapped[process.id] = producer
            self._info('Worker %d initialized.', process.id)
            state = self.manager.get_process(self.process_name)
            if len(self.bootstrapped) >= state.numprocesses:
                self._info('Workers initialization done.')
                self._is_started.set()

        # And bootstrap remote process.
        producer.apply('change_title', args=[name])
        descriptors = {i: listener.name
                       for i, listener in iteritems(self.listeners.enumerated)}
        producer.register_acceptors(descriptors).link(bootstrap_done)

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
        """Handle process events."""
        if msg['name'] != self.process_name:
            # Not our process.
            return

        if evtype == 'exit':
            # Log exit event.
            log = msg['term_signal'] and self._critical or self._info
            log('Worker %d exited with term signal %d and exit status %d.',
                msg['pid'], msg['term_signal'], msg['exit_status'])

        elif evtype == 'spawn':
            # Log spawn event.
            self._info('Worker %d spawned with pid %d.',
                       msg['pid'], msg['os_pid'])

        if not self.controller.is_running:
            # Controller not running, simply exit.
            return

        if evtype == 'spawn':
            # New process spawned, handle event.
            process = self.manager.get_process(msg['pid'])
            self._redirect_io(process)
            self._do_handshake(process)

        elif evtype == 'exit':
            # Process exited, handle event.
            self.bootstrapped.pop(msg['pid'], None)
            producer = self.producers.pop(msg['pid'], None)
            if producer is not None:
                producer.stop()

    @in_loop
    def _pre_start(self):
        manager = self.manager
        manager.subscribe('.', self._on_event)
        manager.add_process(self.process_name,
                            numprocesses=self.app.config.WORKERS,
                            **self._create_arguments())
        manager.start()

    def start(self):
        self._pre_start()
        self._is_started.wait(30.0)
        if not self._is_started.is_set():
            logger.error('Timeout when starting processes.')

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
        processes = parent.processes = \
            ProcessManager(parent.app, parent.listeners, parent)
        return processes
