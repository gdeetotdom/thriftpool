"""Contains patched processor."""
from __future__ import absolute_import

from collections import namedtuple

from thriftworker.utils.proxy import Proxy

from thriftpool import thriftpool
from thriftpool.utils.local import LocalStack


class Request(namedtuple('Request', ('handler', 'method', 'args',
                                     'kwargs', 'service_name'))):
    """Describe thrift request."""


class RequestStack(object):
    """Store thrift requests."""

    Request = Request

    def __init__(self):
        self.stack = LocalStack()

    def add(self, handler, method, args, kwargs, service_name):
        """Register new request."""
        request = self.Request(handler, method, args, kwargs, service_name)
        self.stack.push(request)
        return request

    @property
    def current(self):
        """Return current request."""
        return self.stack.top

    def to_dict(self):
        return {ident: [(request.service_name, request.method.__name__,
                         request.args, request.kwargs)
                        for request in d.get('stack', [])]
                for ident, d in self.stack}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stack.pop()


#: Get current thrift request.
current_request = Proxy(lambda: thriftpool.request_stack.current)
