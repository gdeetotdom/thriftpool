from thriftpool.utils.functional import cached_property
from thriftpool.utils.other import mk_temp_path
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
    def BROKER_ENDPOINT(self):
        return 'ipc://{0}'.format(mk_temp_path(prefix='broker'))
