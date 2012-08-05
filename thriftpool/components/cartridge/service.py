from __future__ import absolute_import
from thriftpool.components.base import StartStopComponent

__all__ = ['ServiceComponent']


class ServiceComponent(StartStopComponent):

    name = 'cartridge.service'

    def create(self, parent):
        return parent.app.MDPService(parent.ident, parent.cartridge)
