from logging.handlers import WatchedFileHandler
from thriftpool.utils.logs import ColorFormatter, ProcessAwareLogger
import logging
import sys

__all__ = ['Logging']

DEFAULT_LOG_FMT = """[%(asctime)s %(levelname)s/%(processName)s] %(message)s"""


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
        self.loglevel = logging.DEBUG
        self.format = DEFAULT_LOG_FMT

    def setup(self):
        ensure_process_aware()
        root = logging.getLogger()
        root.setLevel(self.loglevel)
        self.setup_handlers(root, self.logfile, self.format)

    def get_handler(self, logfile=None):
        """Create log handler with either a filename, an open stream
        or :const:`None` (stderr).

        """
        logfile = sys.stderr if logfile is None else logfile
        if hasattr(logfile, 'write'):
            return logging.StreamHandler(logfile)
        return WatchedFileHandler(logfile)

    def setup_handlers(self, logger, logfile, format, formatter=ColorFormatter,
                       **kwargs):
        """Register needed handlers for given logger. If ``logfile`` equal to 
        :const:`None` use :attribute:`sys.stderr` as ``logfile``.

        """
        colorize = isatty(sys.stderr) if logfile is None else False
        datefmt = '%H:%M:%S' if logfile is None else '%Y-%m-%d %H:%M:%S'
        handler = self.get_handler(logfile)
        handler.setFormatter(formatter(format, use_color=colorize, datefmt=datefmt))
        logger.addHandler(handler)
        return logger
