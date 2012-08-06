from __future__ import absolute_import
from logging import getLogger
from thriftpool.components.base import Namespace
from thriftpool.controllers.base import Controller

__all__ = ['CartridgeController']

logger = getLogger(__name__)


class CartridgeNamespace(Namespace):

    name = 'cartridge'

    def modules(self):
        return ['thriftpool.components.cartridge.service']


class CartridgeController(Controller):

    Namespace = CartridgeNamespace

    def __init__(self, ident, cartridge):
        self.ident = ident
        self.cartridge = cartridge
        super(CartridgeController, self).__init__()

    def on_start(self):
        self.cartridge.on_start()

    def on_shutdown(self):
        self.cartridge.on_stop()
        self.app.hub.stop()
        self.app.context.destroy()
