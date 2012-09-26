from __future__ import absolute_import

from thriftpool.utils.imports import symbol_by_name
from thriftpool.utils.other import rgetattr
from thriftpool.app._state import current_app

__all__ = ['SubclassMixin']


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

        __reduce__ = lambda self: _unpickle, (Class.__name__, [])

        attrs = dict({attribute: self},
                     __module__=Class.__module__,
                     __doc__=Class.__doc__,
                     __reduce__=__reduce__,
                     **kw)

        return type(name or Class.__name__, (Class,), attrs)
