from .encoding import smart_str
from .functional import cached_property
from .term import colored
from billiard.process import current_process
import inspect
import logging

__all__ = ['LogsMixin', 'ColorFormatter', 'ProcessAwareLogger']


class LogsMixin(object):
    """Simple helper for logging."""

    @cached_property
    def _logger(self):
        module = inspect.getmodule(self.__class__)
        return getattr(module, 'logger')

    @cached_property
    def _logger_prefix(self):
        return "(%s@%s) " % (self.__class__.__name__, hex(id(self)))

    def _exception(self, exc):
        self._logger.exception(exc)

    def _error(self, msg, *args, **kwargs):
        self._logger.error(self._logger_prefix + msg, *args, **kwargs)

    def _info(self, msg, *args, **kwargs):
        self._logger.info(self._logger_prefix + msg, *args, **kwargs)

    def _debug(self, msg, *args, **kwargs):
        self._logger.debug(self._logger_prefix + msg, *args, **kwargs)


class ColorFormatter(logging.Formatter):

    #: Loglevel -> Color mapping.
    COLORS = colored().names
    colors = {'DEBUG': COLORS['blue'], 'WARNING': COLORS['yellow'],
              'ERROR': COLORS['red'], 'CRITICAL': COLORS['magenta']}

    def __init__(self, fmt=None, datefmt=None, use_color=True):
        logging.Formatter.__init__(self, fmt, datefmt)
        self.use_color = use_color

    def formatException(self, ei):
        r = logging.Formatter.formatException(self, ei)
        if isinstance(r, str):
            return smart_str(r)
        return r

    def format(self, record):
        levelname = record.levelname
        color = self.colors.get(levelname)

        if self.use_color and color:
            record.msg = smart_str(color(record.msg))

        return smart_str(logging.Formatter.format(self, record))


class ProcessAwareLogger(logging.Logger):

    def makeRecord(self, *args, **kwds):
        record = logging.Logger.makeRecord(self, *args, **kwds)
        record.processName = current_process()._name
        return record
