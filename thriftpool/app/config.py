from __future__ import absolute_import

import logging

from thriftpool.utils.structures import AggregatedView

__all__ = ['Configuration']

DEFAULT_SETTINGS = dict(
    DEBUG=True,
    DEFAULT_LOG_FMT="[%(asctime)s %(levelname)s] %(message)s",
    DEFAULT_WORKER_LOG_FMT="[%(asctime)s %(levelname)s] [%(process)d] %(message)s",
    LOGGING_LEVEL=logging.DEBUG,
    LOG_REQUESTS=False,
    LOG_TORNADO_REQUESTS=False,
    LOG_FILE=None,
    LOG_FORCE_COLORIZED=False,
    REDIRECT_STDOUT=True,
    SLOTS=[],
    PROCESS_NAME='thriftpool',
    MODULES=[],
    PROTOCOL_FACTORY_CLS='thrift.protocol.TBinaryProtocol'
                         ':TBinaryProtocolAcceleratedFactory',
    SERVICE_PORT_RANGE=(10000, 20000),
    WORKER_TYPE='sync',
    WORKERS=1,
    WORKER_TTL=None,
    WORKER_REAP_DELAY=60.0,
    CONCURRENCY=1,
    TORNADO_ENDPOINTS=[],
    #: How long we should wait for process initialization.
    PROCESS_START_TIMEOUT=60.0,
    #: How long we should wait for process termination.
    PROCESS_STOP_TIMEOUT=60.0,
)


class Configuration(AggregatedView):
    """Default application configuration."""

    def __init__(self, config):
        super(Configuration, self).__init__(config)
        self.add_default(DEFAULT_SETTINGS)
