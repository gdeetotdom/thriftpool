"""Some useful tools for logging.

This file was copied and adapted from celery.

:copyright: (c) 2009 - 2012 by Ask Solem.
:license: BSD, see LICENSE for more details.

"""
from __future__ import absolute_import

import logging

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
