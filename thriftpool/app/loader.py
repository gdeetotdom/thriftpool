"""Contains initializer for application."""

__all__ = ['Loader']


class Loader(object):
    """Provide configuration and some callback for main application."""

    app = None

    def get_config(self):
        return {
            'SLOTS': [dict(processor_cls='thriftpool.remote.ThriftPool:Processor',
                           handler_cls='thriftpool.remote.handler:Handler',
                           name='ThriftPool',
                           port=51061)]
        }

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
