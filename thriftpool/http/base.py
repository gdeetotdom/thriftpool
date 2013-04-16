# -*- coding: utf-8 -
from __future__ import absolute_import

import copy
import socket
import logging

# patch tornado IOLoop
from .tornado_pyuv import IOLoop, install
install()

import six
from tornado import netutil
from tornado.web import Application
from tornado.httpserver import HTTPServer

from thriftworker.utils.decorators import cached_property

from .utils import parse_address, is_ipv6
from . import handlers

logger = logging.getLogger(__name__)


DEFAULT_HANDLERS = [
        (r'/', handlers.WelcomeHandler),
        (r'/ping', handlers.PingHandler),
        (r'/version', handlers.VersionHandler),
        (r'/timers', handlers.ClientsHandler),
        (r'/timers/execution/([0-9^/]+)', handlers.ExecutionTimerHandler),
        (r'/timers/dispatching/([0-9^/]+)', handlers.DispatchingTimerHandler),
        (r'/timers/timeouts/([0-9^/]+)', handlers.TimeoutHandler),
        (r'/counters', handlers.ClientsHandler),
        (r'/counters/([0-9^/]+)', handlers.CounterHandler),
        (r'/stack', handlers.ClientsHandler),
        (r'/stack/([0-9^/]+)', handlers.StackHandler),
]


class HttpEndpoint(object):

    def __init__(self, uri='127.0.0.1:5000', backlog=128,
            ssl_options=None):
        # uri should be a list
        if isinstance(uri, six.string_types):
            self.uri = uri.split(",")
        else:
            self.uri = uri
        self.backlog = backlog
        self.ssl_options = ssl_options
        self.server = None
        self.loop = None
        self.io_loop = None

    def __str__(self):
        return ",".join(self.uri)

    def start(self, loop, app):
        for uri in self.uri:
            logger.info('Start new endpoint at http://%s', uri)
        self.loop = loop
        self.app = app
        self.io_loop = IOLoop(_loop=loop)
        self._start_server()

    def _start_server(self):
        self.server = HTTPServer(self.app, io_loop=self.io_loop,
                ssl_options=self.ssl_options)

        # bind the handler to needed interface
        for uri in self.uri:
            addr = parse_address(uri)
            if isinstance(addr, six.string_types):
                sock = netutil.bind_unix_socket(addr)
            elif is_ipv6(addr[0]):
                sock = netutil.bind_sockets(addr[1], address=addr[0],
                        family=socket.AF_INET6, backlog=self.backlog)
            else:
                sock = netutil.bind_sockets(addr[1], backlog=self.backlog)

            if isinstance(sock, list):
                for s in sock:
                    self.server.add_socket(s)
            else:
                self.server.add_socket(sock)

        # start the server
        self.server.start()

    def stop(self):
        self.server.stop()
        self.io_loop.close()

    def restart(self):
        self.server.stop()
        self._start_server()


class HttpHandler(object):
    """Simple container for http handlers."""

    def __init__(self, endpoints=None, handlers=None, **settings):
        self.endpoints = endpoints or []
        if endpoints is None:  # if no endpoints passed add a default
            self.endpoints.append(HttpEndpoint())

        # set http handlers
        self.handlers = copy.copy(DEFAULT_HANDLERS)
        self.handlers.extend(handlers or [])

        # custom settings
        self.settings = settings

    @cached_property
    def app(self):
        return Application(self.handlers, **self.settings)

    def start(self, loop):
        self.loop = loop

        # start endpoints
        for endpoint in self.endpoints:
            endpoint.start(self.loop, self.app)

    def stop(self):
        for endpoint in self.endpoints:
            endpoint.stop()
