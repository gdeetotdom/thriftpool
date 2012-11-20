"""Some useful tools for logging.

This file was copied and adapted from celery.

:copyright: (c) 2009 - 2012 by Ask Solem.
:license: BSD, see LICENSE for more details.

"""
from __future__ import absolute_import

import logging
import sys
import threading
import traceback

from .encoding import smart_str
from .term import colored


LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
    'FATAL': logging.FATAL,
}
LEVELS = {k.lower() for k in LOG_LEVELS.keys()}


def mlevel(level):
    if level and not isinstance(level, int):
        return LOG_LEVELS[level.upper()]
    return level


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


class LoggingProxy(object):
    """Forward file object to :class:`logging.Logger` instance.

    :param logger: The :class:`logging.Logger` instance to forward to.
    :param loglevel: Loglevel to use when writing messages.

    """
    mode = 'w'
    name = None
    closed = False
    loglevel = logging.ERROR
    _thread = threading.local()

    def __init__(self, logger, loglevel=None):
        self.logger = logger
        self.loglevel = loglevel or logging.WARNING
        self._safewrap_handlers()

    def _safewrap_handlers(self):
        """Make the logger handlers dump internal errors to
        `sys.__stderr__` instead of `sys.stderr` to circumvent
        infinite loops."""

        def wrap_handler(handler):                  # pragma: no cover

            class WithSafeHandleError(logging.Handler):

                def handleError(self, record):
                    exc_info = sys.exc_info()
                    try:
                        try:
                            traceback.print_exception(exc_info[0],
                                                      exc_info[1],
                                                      exc_info[2],
                                                      None, sys.__stderr__)
                        except IOError:
                            pass    # see python issue 5971
                    finally:
                        del(exc_info)

            handler.handleError = WithSafeHandleError().handleError

        return [wrap_handler(l) for l in self.logger.handlers]

    def write(self, data):
        """Write message to logging object."""
        if getattr(self._thread, 'recurse_protection', False):
            # Logger is logging back to this file, so stop recursing.
            return
        data = data.strip('\n')
        if data.strip() and not self.closed:
            self._thread.recurse_protection = True
            try:
                self.logger.log(self.loglevel, smart_str(data))
            finally:
                self._thread.recurse_protection = False

    def writelines(self, sequence):
        """`writelines(sequence_of_strings) -> None`.

        Write the strings to the file.

        The sequence can be any iterable object producing strings.
        This is equivalent to calling :meth:`write` for each string.

        """
        for part in sequence:
            self.write(part)

    def flush(self):
        """This object is not buffered so any :meth:`flush` requests
        are ignored."""
        pass

    def close(self):
        """When the object is closed, no write requests are forwarded to
        the logging object anymore."""
        self.closed = True

    def isatty(self):
        """Always returns :const:`False`. Just here for file support."""
        return False

    def fileno(self):
        return None
