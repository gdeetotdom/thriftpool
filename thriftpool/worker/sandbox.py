from __future__ import absolute_import
from thriftpool.worker.abstract import StartStopComponent
import uuid

__all__ = ['SandboxComponent']


class SandboxComponent(StartStopComponent):

    name = 'worker.sandbox'
    requires = ('hub', 'broker')

    def create(self, parent):
        sandbox = parent.sandbox = parent.app.Worker(uuid.uuid4().hex, Sandbox())
        return sandbox


class Sandbox(object):

    def echo(self, s):
        print 'receive', s
        return s
