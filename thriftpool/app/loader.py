"""Contains initializer for application."""
import importlib
from itertools import chain

__all__ = ['Loader']


class Loader(object):
    """Provide configuration and some callback for main application."""

    app = None

    #: Specify modules that should be preloaded.
    builtin_modules = ['thriftpool.remote.handler']

    def get_config(self):
        """Return application configuration."""
        return {}

    def list_modules(self):
        """List all known module names."""
        for module_name in chain.from_iterable((self.builtin_modules,
                                                self.app.config.MODULES)):
            yield module_name

    def import_module(self, module):
        return importlib.import_module(module)

    def preload_modules(self):
        for module_name in self.list_modules():
            self.import_module(module_name)

    def on_before_init(self):
        """Called before controller initialization."""
        pass

    def on_start(self):
        """Called before controller start."""
        pass

    def after_start(self):
        """Called after controller start."""
        pass

    def on_shutdown(self):
        """Called after controller shutdown."""
        pass
