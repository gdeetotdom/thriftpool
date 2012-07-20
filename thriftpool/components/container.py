from __future__ import absolute_import
from thriftpool.components.base import StartStopComponent
from thriftpool.rpc import Worker
import uuid


class ContainerComponent(StartStopComponent):

    name = 'container.container'
    requires = ('hub', )

    def create(self, parent):
        return Worker(parent.app, uuid.uuid4().hex, ContainerHandler())


class ContainerHandler(object):
    pass
