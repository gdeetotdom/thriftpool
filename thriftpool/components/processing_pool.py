"""Contains component that start processing pool."""
from __future__ import absolute_import

from thriftpool.components.base import StartStopComponent


class ProcessingPoolComponent(StartStopComponent):

    name = 'orchestrator.processing_pool'
    requires = ('processor', 'event_loop')

    def create(self, parent):
        """Return processing pool."""
        processing_pool = parent.app.socket_zmq.pool
        return processing_pool
