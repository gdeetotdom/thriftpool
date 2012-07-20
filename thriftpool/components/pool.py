from __future__ import absolute_import
from billiard import Process
from thriftpool.components.base import StartStopComponent


class PoolComponent(StartStopComponent):

    name = 'orchestrator.pool'
    requires = ('broker',)

    def create(self, parent):
        return Pool(parent.app)


class Worker(Process):

    def __init__(self, app):
        self.app = app
        super(Worker, self).__init__()

    def run(self):
        self.app.container.start()


class Pool(object):

    def __init__(self, app):
        self.app = app
        self.process = Worker(self.app)

    def start(self):
        self.process.start()

    def stop(self):
        self.process.terminate()
