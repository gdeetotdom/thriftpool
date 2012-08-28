from thriftpool.utils.functional import cached_property
from thriftpool.utils.structures import AggregatedView
import logging

__all__ = ['Configuration']

DEFAULT_SETTINGS = dict(
    DEBUG=True,
    DEFAULT_LOG_FMT="[%(asctime)s %(levelname)s/%(processName)s] %(message)s",
    LOGGING_LEVEL=logging.DEBUG,
    LOG_REQUESTS=False,
    SLOTS=[],
)


class Configuration(AggregatedView):
    """Default application configuration."""

    def __init__(self, config):
        super(Configuration, self).__init__(config)
        self.add_default(DEFAULT_SETTINGS)

    @cached_property
    def FRONTEND_ENDPOINT(self):
        return 'inproc://frontend{0}'.format(id(self))

    @cached_property
    def BACKEND_ENDPOINT(self):
        return 'inproc://backend{0}'.format(id(self))
