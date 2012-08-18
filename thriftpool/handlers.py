"""Provide some tools to patch thrift handler."""
from functools import wraps
from thrift.Thrift import TApplicationException, TMessageType
from thriftpool.signals import handler_method_guarded
import inspect
import logging

__all__ = ['HandlerMeta', 'ProcessorMixin']


def method_guard(cls, fn):
    """Protect thrift service from missed exceptions."""

    # Apply all returned by signal decorators.
    for sender, decorator in handler_method_guarded.send(sender=cls, fn=fn):
        if decorator is not None:
            fn = decorator(fn)

    @wraps(fn)
    def inner(*args, **kwargs):
        try:
            return fn(*args, **kwargs)

        except Exception as exc:
            # Catch all exceptions here, process they here. Write application
            # exception to thrift transport.
            logging.exception(exc)
            raise TApplicationException(TApplicationException.INTERNAL_ERROR, str(exc))

    return inner


class HandlerMeta(type):
    """Metaclass that create handler with decorated methods."""

    def __new__(mcs, name, bases, attrs):
        # Try to find methods of service.
        included = set()
        stack = set(bases)
        while stack:
            # Collect all bases and try to find all classes with name 'Iface'.
            # Methods with collected names will be decorated.
            base = stack.pop()
            if base is object:
                continue
            stack.update(base.__bases__)
            if base.__name__ == 'Iface':
                included.update(vars(base).keys())

        # No interface found, simply create class.
        if not included:
            return type.__new__(mcs, name, bases, attrs)

        # Find attributes that must be decorated.
        included = included - set(vars(type).keys() + ['__weakref__'])

        # Create new class.
        cls = type.__new__(mcs, name, bases, attrs)

        # Decorate them!
        for attr in included:
            fn = getattr(cls, attr)
            if not inspect.ismethod(fn):
                # Decorate only methods.
                continue
            setattr(cls, attr, method_guard(cls, fn))

        return cls


class ProcessorMixin(object):
    """Process application error if there is one."""

    def process(self, iprot, oprot):
        name, type, seqid = iprot.readMessageBegin()

        try:
            try:
                fn = self._processMap[name]
            except KeyError:
                raise TApplicationException(TApplicationException.UNKNOWN_METHOD,
                                            'Unknown function %s' % (name))
            else:
                fn(self, seqid, iprot, oprot)

        except TApplicationException as exc:
            oprot.writeMessageBegin(name, TMessageType.EXCEPTION, seqid)
            exc.write(oprot)
            oprot.writeMessageEnd()
            oprot.trans.flush()
            return

        return True
