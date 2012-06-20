from thriftpool.utils.functional import cached_property
from thriftpool.utils.imports import symbol_by_name

__all__ = ['ThriftPool']


class ThriftPool(object):

    #: Describe which class should used as application controller.
    controller_cls = 'thriftpool.worker.controller:Controller'

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

        attrs = dict({attribute: self}, __module__=Class.__module__,
                     __doc__=Class.__doc__, **kw)

        return type(name or Class.__name__, (Class,), attrs)

    @cached_property
    def Controller(self):
        return self.subclass_with_self(self.controller_cls)

    @cached_property
    def controller(self):
        return self.Controller()
