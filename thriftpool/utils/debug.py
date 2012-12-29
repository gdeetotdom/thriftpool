"""Some useful class for request logging."""
from __future__ import absolute_import

from functools import wraps
import time
import sys
import inspect
import itertools
from pprint import pformat

from thriftpool.signals import handler_method_guarded

if sys.platform == "win32":
    # On Windows, the best timer is time.clock()
    default_timer = time.clock
else:
    # On most other platforms the best timer is time.time()
    default_timer = time.time


NEW_REQUEST_MESSAGE = \
    """{prefix} do {method_name} where
    arguments = {arguments}
    keywords  = {keywords}"""

SERVED_REQUEST_MESSAGE = \
    """{prefix} return {result} ({took})"""


def qualname(obj):
    if not hasattr(obj, '__name__') and hasattr(obj, '__class__'):
        return qualname(obj.__class__)

    return '%s.%s' % (obj.__module__, obj.__name__)


class RequestLogger(object):

    def __init__(self, logger, colored):
        self.logger = logger
        self.colored = colored
        self.counter = itertools.cycle(xrange(2 ** 16))

    def setup(self):
        handler_method_guarded.connect(self.decorate)

    def decorate(self, signal, sender, fn):
        method_name = "{0}.{1}".format(qualname(sender), fn.__name__)
        method_args = inspect.getargspec(fn).args
        if inspect.ismethod(fn) and method_args:
            method_args.pop(0)
        blue = self.colored.blue
        black = self.colored.black
        magenta = self.colored.magenta

        def decorator(func):
            @wraps(func)
            def inner(*args, **kwargs):
                request = self.counter.next()
                # Log incoming request.
                arguments = []
                keywords = {}
                if method_args:
                    keywords.update(dict(zip(method_args[:len(args)], args)))
                else:
                    arguments = args
                keywords.update(kwargs)
                self.logger.info(NEW_REQUEST_MESSAGE.format(
                    prefix=magenta('In [{0}]:'.format(request)),
                    method_name=blue(method_name),
                    arguments=blue(pformat(arguments)),
                    keywords=blue(pformat(keywords)),
                ))
                # Measure time.
                start = default_timer()
                result = func(*args, **kwargs)
                duration = default_timer() - start
                # Log response.
                self.logger.info(SERVED_REQUEST_MESSAGE.format(
                    prefix=black('Out [{0}]:'.format(request)),
                    took='{:.3f} ms'.format(duration * 1000)
                         if duration < 0.001
                         else '{:.3f} s'.format(duration),
                    result=blue(pformat(result)),
                ))
                return result
            return inner

        return decorator
