from .functional import cached_property
import inspect

__all__ = ['LogsMixin']


class LogsMixin(object):
    """Simple helper for logging."""

    @cached_property
    def _logger(self):
        module = inspect.getmodule(self.__class__)
        return getattr(module, 'logger')

    @cached_property
    def _logger_prefix(self):
        return "[%s@%s] " % (self.__class__.__name__, hex(id(self)))

    def _exception(self, exc):
        self._logger.exception(exc)

    def _error(self, msg, *args, **kwargs):
        self._logger.error(self._logger_prefix + msg, *args, **kwargs)

    def _info(self, msg, *args, **kwargs):
        self._logger.info(self._logger_prefix + msg, *args, **kwargs)

    def _debug(self, msg, *args, **kwargs):
        self._logger.debug(self._logger_prefix + msg, *args, **kwargs)
