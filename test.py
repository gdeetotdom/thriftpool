import sys
from logging import basicConfig, DEBUG
import pyev
basicConfig(level=DEBUG)

from thriftpool.app.base import ThriftPool

app = ThriftPool()

controller = app.controller
controller.start()
