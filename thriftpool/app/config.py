from __future__ import absolute_import

import logging

from thriftpool.utils.structures import AggregatedView

__all__ = ['Configuration']

DEFAULT_SETTINGS = dict(
    DEBUG=True,
    DEFAULT_LOG_FMT="[%(asctime)s %(levelname)s] %(message)s",
    LOGGING_LEVEL=logging.DEBUG,
    LOG_REQUESTS=False,
    LOG_FILE=None,
    SLOTS=[],
    PROCESS_NAME='thriftpool',
    MODULES=[],
    PROTOCOL_FACTORY_CLS='thrift.protocol.TBinaryProtocol'
                         ':TBinaryProtocolAcceleratedFactory',
)


class Configuration(AggregatedView):
    """Default application configuration."""

    def __init__(self, config):
        super(Configuration, self).__init__(config)
        self.add_default(DEFAULT_SETTINGS)
