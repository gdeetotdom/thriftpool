"""Start and stop http handlers."""
from __future__ import absolute_import

import logging

from thriftworker.utils.mixin import LoopMixin
from thriftworker.utils.loop import in_loop
from thriftworker.utils.decorators import cached_property

from thriftpool.components.base import StartStopComponent
from thriftpool.http import HttpEndpoint, HttpHandler

logger = logging.getLogger(__name__)


class TornadoManager(LoopMixin):
    """Start and stop tornado."""

    def __init__(self, app, processes):
        self.app = app
        self.processes = processes
        super(TornadoManager, self).__init__()

    @cached_property
    def handler(self):
        endpoints = self.app.config.TORNADO_ENDPOINTS
        return HttpHandler(
            log_function=self.app.log.log_tornado_request,
            endpoints=[HttpEndpoint(uri=uri) for uri in endpoints],
            processes=self.processes,
        )

    @in_loop
    def start(self):
        self.handler.start(self.loop)

    @in_loop
    def stop(self):
        self.handler.stop()
        del self.handler


class TornadoComponent(StartStopComponent):

    name = 'manager.tornado'
    requires = ('loop', 'processes')

    def create(self, parent):
        return TornadoManager(parent.app, parent.processes)
