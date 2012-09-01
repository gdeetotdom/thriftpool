from thriftpool.utils.structures import AggregatedView
import logging

__all__ = ['Configuration']

DEFAULT_SETTINGS = dict(
    DEBUG=True,
    DEFAULT_LOG_FMT="[%(asctime)s %(levelname)s] %(message)s",
    LOGGING_LEVEL=logging.DEBUG,
    LOG_REQUESTS=True,
    SLOTS=[],
)


class Configuration(AggregatedView):
    """Default application configuration."""

    def __init__(self, config):
        super(Configuration, self).__init__(config)
        self.add_default(DEFAULT_SETTINGS)
