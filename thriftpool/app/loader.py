"""Contains initializer for application."""
from thriftpool.utils.structures import AttributeDict
from thriftpool.utils.other import mk_temp_path

__all__ = ['Loader']


class Loader(object):
    """Provide configuration and some callback for main application."""

    app = None

    def __init__(self):
        self._config = AttributeDict(DEBUG=True)

    def get_config(self):
        return self._config

    def on_before_init(self):
        self.app.log.setup()

    def on_start(self):
        """Called before controller starts."""
        self._config.update(BROKER_ENDPOINT='ipc://{0}'.format(mk_temp_path()))

    def on_shutdown(self):
        """Called after controller shutdown."""
        pass
