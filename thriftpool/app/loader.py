"""Contains initializer for application."""

__all__ = ['Loader']


class Loader(object):
    """Provide configuration and some callback for main application."""

    app = None

    def get_config(self):
        return {}

    def on_before_init(self):
        pass

    def on_start(self):
        """Called before controller starts."""
        pass

    def on_shutdown(self):
        """Called after controller shutdown."""
        pass
