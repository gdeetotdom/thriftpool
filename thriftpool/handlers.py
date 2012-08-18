"""Provide some tools to patch thrift handler."""
from functools import wraps
from thrift.Thrift import TApplicationException, TMessageType
import inspect
import logging

__all__ = ['HandlerMeta', 'ProcessorMixin']


def method_guard(fn):
    """Protect thrift service from missed exceptions."""

    @wraps(fn)
    def inner(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            logging.exception(exc)
            raise TApplicationException(TApplicationException.INTERNAL_ERROR, str(exc))

    return inner


class HandlerMeta(type):
    """Create decorated handler."""

    def __new__(mcs, name, bases, attrs):
        # Try to find methods of service.
        included = set()
        stack = set(bases)
        while stack:
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
            setattr(cls, attr, method_guard(fn))

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
