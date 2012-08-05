from thriftpool.utils.functional import cached_property

__all__ = ['Cartridge', 'ControllerCartridge']


class Cartridge(object):

    def __init__(self, app):
        self.app = app

    def on_start(self):
        pass

    def on_stop(self):
        pass


class ControllerCartridge(Cartridge):

    @cached_property
    def controller(self):
        return self.create()

    def create(self):
        raise NotImplementedError()

    def on_start(self):
        self.controller.start()

    def on_stop(self):
        self.controller.stop()
