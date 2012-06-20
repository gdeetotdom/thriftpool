from logging import basicConfig, DEBUG
basicConfig(level=DEBUG)

from thriftpool.app.base import ThriftPool

app = ThriftPool()

controller = app.controller
controller.start()
