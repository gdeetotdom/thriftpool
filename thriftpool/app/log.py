"""Configure logging subsystem."""
from __future__ import absolute_import

from logging.handlers import WatchedFileHandler
import logging
import sys
import os

from thriftpool.signals import setup_logging, after_logging_setup
from thriftpool.utils.logs import ColorFormatter
from thriftpool.utils.term import colored, isatty
from thriftpool.utils.debug import RequestLogger

__all__ = ['Logging']


class Logging(object):
    """Setup logging subsystem."""

    app = None

    def __init__(self):
        config = self.app.config
        logfile = self.logfile = config.LOG_FILE
        self.loglevel = config.LOGGING_LEVEL
        self.format = config.DEFAULT_WORKER_LOG_FMT \
                      if os.getenv('IS_WORKER', False) \
                      else config.DEFAULT_LOG_FMT
        colorized = config.LOG_FORCE_COLORIZED = self.colorized = \
            config.LOG_FORCE_COLORIZED or self.colorize(logfile)
        self.colored = colored(enabled=colorized)
        self.request_logger = None
        self.tornado_logger = None

    def get_handler(self, logfile=None):
        """Create log handler with either a filename, an open stream
        or :const:`None` (stderr).

        """
        logfile = sys.stderr if logfile is None else logfile
        if hasattr(logfile, 'write'):
            return logging.StreamHandler(logfile)
        return WatchedFileHandler(logfile)

    def colorize(self, logfile=None):
        """Can be output colored?"""
        return isatty(sys.stderr) if logfile is None else False

    def setup_handlers(self, logger, logfile, format,
                       formatter=ColorFormatter):
        """Register needed handlers for given logger. If ``logfile`` equal to
        :const:`None` use :attr:`sys.stderr` as ``logfile``.

        """
        colorize = self.colorize(logfile)
        datefmt = '%H:%M:%S' if logfile is None else '%Y-%m-%d %H:%M:%S'
        handler = self.get_handler(logfile)
        handler.setFormatter(formatter(format, use_color=colorize,
                                       datefmt=datefmt))
        logger.addHandler(handler)
        return logger

    def setup_request_logging(self):
        """Setup system to log requests."""
        logger = logging.getLogger('thriftpool.requests')
        self.request_logger = RequestLogger(logger, self.colored)
        self.request_logger.setup()

    def setup_tornado_logger(self):
        self.tornado_logger = logging.getLogger('thriftpool.tornado')

    def setup(self):
        root = logging.getLogger()
        root.setLevel(self.loglevel)
        receivers = setup_logging.send(sender=self, root=root,
                                       logfile=self.logfile,
                                       loglevel=self.loglevel)
        if not receivers:
            self.setup_handlers(root, self.logfile, self.format)
            after_logging_setup.send(sender=self, root=root,
                                     logfile=self.logfile,
                                     loglevel=self.loglevel)
        if self.app.config.LOG_REQUESTS:
            self.setup_request_logging()
        if self.app.config.LOG_TORNADO_REQUESTS:
            self.setup_tornado_logger()

    def log_tornado_request(self, handler):
        logger = self.tornado_logger
        if logger is None:
            return
        if handler.get_status() < 400:
            log_method = logger.info
        elif handler.get_status() < 500:
            log_method = logger.warning
        else:
            log_method = logger.error
        request_time = 1000.0 * handler.request.request_time()
        log_method("%d %s %.2fms", handler.get_status(),
                   handler._request_summary(), request_time)
