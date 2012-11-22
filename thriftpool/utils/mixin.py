from __future__ import absolute_import

import inspect

from thriftworker.utils.decorators import cached_property
from thriftworker.utils.imports import symbol_by_name

from thriftpool.app._state import current_app


def rgetattr(obj, path):
    """Get nested attribute from object.

    :param obj: object
    :param path: path to attribute

    """
    return reduce(getattr, [obj] + path.split('.'))


def _unpickle(name, args):
    """Given an attribute name and a list of args, gets
    the attribute from the current app and calls it.

    """
    return rgetattr(current_app, name)(*args)


class SubclassMixin(object):

    def subclass_with_self(self, Class, name=None, attribute='app',
                           reverse=None, **kw):
        """Subclass an app-compatible class by setting its app attribute
        to be this app instance.

        App-compatible means that the class has a class attribute that
        provides the default app it should use, e.g.
        ``class Foo: app = None``.

        :param Class: The app-compatible class to subclass.
        :keyword name: Custom name for the target class.
        :keyword attribute: Name of the attribute holding the app,
                            default is 'app'.

        """
        Class = symbol_by_name(Class)
        reverse = reverse if reverse else Class.__name__
        has_reduce_args = getattr(Class, '__reduce_args__', None) is not None

        def __reduce__(self):
            args = self.__reduce_args__() if has_reduce_args else []
            return (_unpickle, (Class.__name__, args))

        attrs = dict({attribute: self},
                     __module__=Class.__module__,
                     __doc__=Class.__doc__,
                     __reduce__=__reduce__,
                     **kw)

        return type(name or Class.__name__, (Class,), attrs)


class LogsMixin(object):
    """Simple helper for logging."""

    @cached_property
    def _logger(self):
        module = inspect.getmodule(self.__class__)
        return getattr(module, 'logger')

    def _exception(self, exc):
        self._logger.exception(exc)

    def _critical(self, msg, *args, **kwargs):
        self._logger.critical(msg, *args, **kwargs)

    def _error(self, msg, *args, **kwargs):
        self._logger.error(msg, *args, **kwargs)

    def _info(self, msg, *args, **kwargs):
        self._logger.info(msg, *args, **kwargs)

    def _debug(self, msg, *args, **kwargs):
        self._logger.debug(msg, *args, **kwargs)
