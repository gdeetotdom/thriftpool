"""Manage process pool."""
from __future__ import absolute_import

import json
import logging
import sys
import os

from gaffer.http.util import CorsHandler
from gaffer.http_handler import HttpHandler, HttpEndpoint
from pyuv import Pipe
from six import iteritems

from thriftworker.utils.loop import in_loop
from thriftworker.utils.decorators import cached_property
from thriftworker.utils.mixin import LoopMixin

from thriftpool.app import current_app
from thriftpool.exceptions import SystemTerminate
from thriftpool.utils.mixin import LogsMixin
from thriftpool.utils.serializers import StreamSerializer
from thriftpool.rpc.manager import Clients

from .base import StartStopComponent

logger = logging.getLogger(__name__)


#: How long we should wait for process initialization.
START_TIMEOUT = 60.0

#: How long we should wait for process termination.
STOP_TIMEOUT = 60.0


class BaseHandler(CorsHandler):

    def initialize(self, clients):
        self._clients = clients

    def _execute(self, *args, **kwargs):
        execute = super(BaseHandler, self)._execute
        current_app.hub.spawn(execute, *args, **kwargs)


class ClientsHandler(BaseHandler):

    def get(self):
        self.preflight()
        self.set_status(200)
        self.write(json.dumps(self._clients.keys()))


class BaseClientHandler(BaseHandler):

    def get_data(self, proxy):
        raise NotImplementedError('subclass responsibility')

    def get(self, *args):
        self.preflight()

        try:
            pid = int(args[0])
        except ValueError:
            self.set_status(400)
            self.write({"error": "bad_value"})
            return

        if pid in self._clients:
            self.set_status(200)
        else:
            self.set_status(404)
            return

        client = self._clients[pid]
        data = client.spawn(self.get_data).get()
        self.write(json.dumps(data))


class CounterHandler(BaseClientHandler):

    def get_data(self, proxy):
        return {'{0}.{1}'.format(service, method): value
                for (service, method), value in proxy.get_counters().items()}


class TimerHandler(BaseClientHandler):

    def get_data(self, proxy):
        return {'{0}.{1}'.format(service, method): value
                for (service, method), value in proxy.get_timers().items()}


class StackHandler(BaseClientHandler):

    def get_data(self, proxy):
        return {ident: [{'method': '{0}.{1}'.format(service, method),
                         'args': repr(args), 'kwargs': repr(kwargs)}
                        for (service, method, args, kwargs) in l]
                for ident, l in proxy.get_stack().items()}


class RedirectStream(object):
    """Try to write to stream asynchronous."""

    def __init__(self, loop, stream):
        self.fd = None
        self.stream = stream
        try:
            fd = self.fd = stream.fileno()
        except AttributeError:
            self.channel = None
        else:
            channel = self.channel = Pipe(loop)
            setattr(channel, 'bypass', True)
            channel.open(fd)

    def write(self, data):
        """Write data in asynchronous way."""
        if self.channel is not None and not self.channel.closed:
            self.channel.write(data)
        else:
            self.stream.write(data)


class ProcessManager(LogsMixin, LoopMixin):
    """Start and manage workers."""

    process_name = 'worker'
    name_template = '[thriftworker-{0}]' \
                    ' -c {1.CONCURRENCY}' \
                    ' -k {1.WORKER_TYPE}'
    gevent_monkey = 'from gevent.monkey import patch_all; patch_all();'
    script = 'from thriftpool.bin.thriftworker import main; main();'

    def __init__(self, app, listeners, controller):
        self.clients = Clients()
        self.serializers = StreamSerializer()
        self.app = app
        self.listeners = listeners
        self.controller = controller
        self._bootstrapped = set()
        super(ProcessManager, self).__init__()

    @property
    def manager(self):
        return self.app.gaffer_manager

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

    def _bootstrap_process(self, proxy, process):
        # Change name of process.
        name = self.name_template.format(process.id, self.app.config)
        proxy.change_title(name)

        # Register acceptors in remote process.
        proxy.register_acceptors({i: listener.name
            for i, listener in iteritems(self.listeners.enumerated)})

        for listener in self.listeners:
            if listener.started:
                proxy.start_acceptor(listener.name)

        # Notify about process initialization.
        self._bootstrapped.add(process.id)
        self._info('Worker %d initialized.', process.id)
        state = self.manager.get_process(self.process_name)
        if len(self._bootstrapped) >= state.numprocesses:
            self._info('Workers initialization done.')
            self._is_started.set()

    def _do_handshake(self, process):
        # Pass application to created process.
        stream = process.streams['handshake']
        stream.write(self.serializers.encode_with_length(self.app))

        def handshake_done(evtype, info):
            stream.unsubscribe(handshake_done)
            # Process exited and we do the same.
            if not process.active:
                return
            self.clients.register(process, self._bootstrap_process)

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

        if evtype == 'spawn' and self.controller.is_running:
            # New process spawned, handle event.
            process = self.manager.get_process(msg['pid'])
            self._redirect_io(process)
            self._do_handshake(process)

        elif evtype == 'exit':
            # Process exited, handle event.
            self._bootstrapped.remove(msg['pid'])
            self.clients.unregister(msg['pid'])

    def _create_proc_kwargs(self):
        """Create arguments for worker."""
        config = self.app.config
        worker_type = config.WORKER_TYPE
        if worker_type == 'gevent':
            startup_line = '{0} {1}'.format(self.gevent_monkey, self.script)
        elif worker_type == 'sync':
            startup_line = self.script
        else:
            raise NotImplementedError()
        return dict(cmd=sys.executable,
                    args=['-c', '{0}'.format(startup_line)],
                    redirect_output=['out', 'err'],
                    custom_streams=['handshake', 'incoming', 'outgoing'],
                    custom_channels=self.listeners.channels,
                    env=dict(os.environ, IS_WORKER='1'),
                    numprocesses=config.WORKERS,
                    redirect_input=True,
                    graceful_timeout=STOP_TIMEOUT / 2)

    def _create_apps(self):
        """Create applications for gaffer."""
        apps = []
        options = dict(clients=self.clients)
        handlers = [
            (r'/timers', ClientsHandler, options),
            (r'/timers/([0-9^/]+)', TimerHandler, options),
            (r'/counters', ClientsHandler, options),
            (r'/counters/([0-9^/]+)', CounterHandler, options),
            (r'/stack', ClientsHandler, options),
            (r'/stack/([0-9^/]+)', StackHandler, options),
        ]
        endpoints = self.app.config.TORNADO_ENDPOINTS
        if endpoints:
            apps.append(HttpHandler(handlers=handlers,
                log_function=self.app.log.log_tornado_request,
                endpoints=[HttpEndpoint(uri=uri) for uri in endpoints]))
        return apps

    @in_loop
    def _setup(self):
        manager = self.manager
        manager.subscribe('.', self._on_event)
        manager.add_process(self.process_name, **self._create_proc_kwargs())
        manager.start(apps=self._create_apps())

    def start(self):
        self._setup()
        self._is_started.wait(START_TIMEOUT)
        if not self._is_started.is_set():
            self._error('Timeout when starting processes.')
            self._teardown()
            raise SystemTerminate()

    @in_loop
    def _teardown(self):
        self.clients.clear()
        stop_callback = lambda *args: self._is_stopped.set()
        self.manager.stop(stop_callback)

    def stop(self):
        self._teardown()
        self._is_stopped.wait(STOP_TIMEOUT)
        if not self._is_stopped.is_set():
            self._error('Timeout when terminating processes.')
            raise SystemTerminate()


class ProcessManagerComponent(StartStopComponent):

    name = 'manager.process_manager'
    requires = ('loop', 'listeners')

    def create(self, parent):
        processes = parent.processes = \
            ProcessManager(parent.app, parent.listeners, parent)
        return processes
