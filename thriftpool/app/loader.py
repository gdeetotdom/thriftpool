"""Contains initializer for application."""
from __future__ import absolute_import

import importlib
from itertools import chain

try:
    from pkg_resources import iter_entry_points
except ImportError:
    iter_entry_points = lambda *args, **kwargs: []

from thriftworker.utils.imports import import_from_cwd

from thriftpool import signals

__all__ = ['Loader']


class Loader(object):
    """Provide configuration and some callback for main application."""

    app = None

    #: Specify modules that should be preloaded.
    builtin_modules = ['thriftpool.remote.handler']

    def get_config(self):
        """Return application configuration."""
        return {}

    def entrypoint_modules(self):
        """List all modules that are registered through setuptools
        entry points.

        """
        modules = []
        for entrypoint in iter_entry_points(group='thriftpool.modules'):
            # Grab the function that is the actual plugin.
            module_provider = entrypoint.load()
            modules.extend(module_provider(self.app))
        return modules

    def list_modules(self):
        """List all known module names."""
        for module_name in chain.from_iterable((self.builtin_modules,
                                                self.entrypoint_modules(),
                                                self.app.config.MODULES)):
            yield module_name

    def import_module(self, module):
        return import_from_cwd(module)

    def preload_modules(self):
        for module_name in self.list_modules():
            self.import_module(module_name)

    def on_before_init(self, controller):
        """Called before controller initialization."""
        pass

    def on_start(self):
        """Called before controller start."""
        signals.app_start.send(sender=self, app=self.app)

    def after_start(self):
        """Called after controller start."""
        signals.after_app_start.send(sender=self, app=self.app)

    def on_shutdown(self):
        """Called after controller shutdown."""
        signals.app_shutdown.send(sender=self, app=self.app)

    def after_unpickling(self):
        """Called after application was unpickled."""
        pass
