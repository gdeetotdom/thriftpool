"""Provide some tools to patch thrift handler."""
from __future__ import absolute_import

import logging
from functools import wraps

from thrift.Thrift import TApplicationException, TException
from thrift.protocol.TBase import TExceptionBase

from thriftpool import thriftpool
from thriftpool.signals import handler_method_guarded
from thriftpool.exceptions import WrappingError

logger = logging.getLogger(__name__)


class guarded_method(object):
    """Create guarded method for handler."""

    def __init__(self, name, doc):
        self.__name__ = name
        self.__doc__ = doc

    def __create_method(self, obj):
        """Create bounded method."""
        handler = obj._handler
        service_name = obj._service_name
        method = getattr(handler, self.__name__)
        stack = thriftpool.request_stack
        allowed_exceptions = (TException, TExceptionBase)

        # Apply all returned by signal decorators.
        for sender, decorator in handler_method_guarded.send(sender=handler,
                                                             fn=method):
            if decorator is not None:
                method = decorator(method)

        @wraps(method)
        def inner_method(*args, **kwargs):
            """Method that handle unknown exception correctly."""
            stack.add(handler, method, args, kwargs, service_name)
            with stack:
                try:
                    return method(*args, **kwargs)
                except allowed_exceptions:
                    raise
                except Exception as exc:
                    # Catch all exceptions here, process they here. Write
                    # application exception to thrift transport.
                    logger.exception(exc)
                    code = TApplicationException.INTERNAL_ERROR
                    msg = "({0}) {1}".format(type(exc).__name__, str(exc))
                    raise TApplicationException(code, msg)

        return inner_method

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        try:
            return obj.__dict__[self.__name__]
        except KeyError:
            value = obj.__dict__[self.__name__] = self.__create_method(obj)
            return value


class BaseWrappedHandler(object):
    """Abstract base for wrapped handler."""

    _handler_cls = None
    _service_name = None
    _wrapped_methods = None

    def __init__(self, handler):
        self._handler = handler
        # Force methods creation.
        for item in self._wrapped_methods:
            getattr(self, item)

    def __getattr__(self, name):
        """All unknown attribute access go to wrapped handler."""
        return getattr(self._handler, name)


class WrappedHandlerMeta(type):
    """Metaclass that create handler with decorated methods."""

    def __new__(mcs, name, bases, attrs):
        # Add base class to bases.
        if BaseWrappedHandler not in bases:
            bases = (BaseWrappedHandler,) + bases
        # Ensure that service name provided.
        if '_service_name' not in attrs:
            raise WrappingError('Missing attribute "_service_name" in'
                                ' class "{0}"'.format(name))
        # Get original handler class.
        try:
            handler_cls = attrs['_handler_cls']
        except KeyError:
            raise WrappingError('Missing attribute "_handler_cls" in'
                                ' class "{0}"'.format(name))
        # Try to find methods of service.
        included = set()
        stack = set(handler_cls.__bases__)
        while stack:
            # Collect all bases and try to find all classes with name 'Iface'.
            # Methods with collected names will be decorated.
            base = stack.pop()
            if base is object:
                continue
            stack.update(base.__bases__)
            if base.__name__ == 'Iface':
                included.update(vars(base).keys())

        # No interface found, fail.
        if not included:
            raise WrappingError('No methods to wrap found in class "{0}"'.
                                format(name))

        # Find attributes that must be decorated.
        included = included - set(vars(type).keys() + ['__weakref__'])
        attrs['_wrapped_methods'] = included

        # Decorate them!
        for attr in included:
            method = guarded_method(attr, getattr(handler_cls, attr).__doc__)
            attrs[attr] = method

        # Create new class.
        return super(WrappedHandlerMeta, mcs).__new__(mcs, name, bases, attrs)
