from __future__ import absolute_import

import os
import contextlib
from functools import partial

from unittest import TestCase as BaseTestCase

from thriftpool.app import _state as state


@contextlib.contextmanager
def change_cwd(cwd):
    """Temporary change current directory."""
    current_cwd = os.getcwd()
    os.chdir(cwd)
    try:
        yield
    finally:
        os.chdir(current_cwd)


@contextlib.contextmanager
def custom_settings(app, **kwargs):
    """Temporarily change settings."""
    variables = vars(app.config)
    original_underlying_dicts = variables['_underlying_dicts']
    variables['_underlying_dicts'] = [kwargs] + original_underlying_dicts
    try:
        yield
    finally:
        variables['_underlying_dicts'] = original_underlying_dicts


class Noop(object):
    """Object that do nothing."""


class TestCase(BaseTestCase):

    def setUp(self):
        # reset current state before each run
        state.default_app = None
        app = self.app = state.get_current_app()
        self.custom_settings = partial(custom_settings, app)
