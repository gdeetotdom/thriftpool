from functools import wraps
from logging.handlers import WatchedFileHandler
from thriftpool.signals import handler_method_guarded
from thriftpool.utils.logs import (ColorFormatter, ProcessAwareLogger,
    LoggingProxy)
from thriftpool.utils.term import colored
import logging
import sys
import time

if sys.platform == "win32":
    # On Windows, the best timer is time.clock()
    default_timer = time.clock
else:
    # On most other platforms the best timer is time.time()
    default_timer = time.time

__all__ = ['Logging']


def isatty(stream):
    return hasattr(stream, 'isatty') and stream.isatty()


def ensure_process_aware():
    logging._acquireLock()
    try:
        logging.setLoggerClass(ProcessAwareLogger)
    finally:
        logging._releaseLock()


class Logging(object):
    """Setup logging subsystem."""

    app = None

    def __init__(self):
        self.logfile = None
        self.loglevel = self.app.config.LOGGING_LEVEL
        self.format = self.app.config.DEFAULT_LOG_FMT
        self.colored = colored(enabled=self.colorize(self.logfile))
        self.request_logger = None

    def redirect_stdouts_to_logger(self, logger, loglevel=None,
            stdout=True, stderr=True):
        """Redirect :class:`sys.stdout` and :class:`sys.stderr` to a
        logging instance.

        :param logger: The :class:`logging.Logger` instance to redirect to.
        :param loglevel: The loglevel redirected messages will be logged as.

        """
        proxy = LoggingProxy(logger, loglevel)
        if stdout:
            sys.stdout = proxy
        if stderr:
            sys.stderr = proxy
        return proxy

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

    def setup_handlers(self, logger, logfile, format, formatter=ColorFormatter):
        """Register needed handlers for given logger. If ``logfile`` equal to 
        :const:`None` use :attribute:`sys.stderr` as ``logfile``.

        """
        colorize = self.colorize(logfile)
        datefmt = '%H:%M:%S' if logfile is None else '%Y-%m-%d %H:%M:%S'
        handler = self.get_handler(logfile)
        handler.setFormatter(formatter(format, use_color=colorize, datefmt=datefmt))
        logger.addHandler(handler)
        return logger

    def setup_request_logging(self):
        """Setup system to log requests."""
        self.request_logger = logging.getLogger('thriftpool.requests')

    def decorate_request(self, signal, sender, fn):
        """Decorate every method to log requests."""
        method_name = "{0}::{1}".format(sender.__name__, fn.__name__)

        def decorator(func):
            @wraps(func)
            def inner(*args, **kwargs):
                start = default_timer()
                result = func(*args, **kwargs)
                duration = default_timer() - start
                took = ('{:.3f} ms'.format(duration * 1000)
                        if duration < 0.001
                        else '{:.3f} s'.format(duration))
                self.request_logger.info("[%s] took %s",
                                         self.colored.green(method_name),
                                         took)
                return result
            return inner

        return decorator

    def setup(self):
        ensure_process_aware()
        root = logging.getLogger()
        root.setLevel(self.loglevel)
        self.setup_handlers(root, self.logfile, self.format)
        self.redirect_stdouts_to_logger(root)
        if self.app.config.LOG_REQUESTS:
            self.setup_request_logging()
            handler_method_guarded.connect(self.decorate_request)

