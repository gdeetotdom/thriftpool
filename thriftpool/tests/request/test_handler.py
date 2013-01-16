# -*- coding: utf-8 -*-
from __future__ import absolute_import

from mock import Mock
from thrift.Thrift import TException, TApplicationException

from thriftpool.tests.utils import TestCase
from thriftpool.exceptions import WrappingError
from thriftpool.remote.ThriftPool import Iface
from thriftpool.request.handler import guarded_method, BaseWrappedHandler, \
    WrappedHandlerMeta


class UnknownException(Exception):
    pass


class NotFound(TException):
    pass


class Handler(Iface):

    def ping(self):
        pass


class WrongHandler(object):

    def ping(self):
        pass


class TestGuardedMethod(TestCase):

    def setUp(self):
        methods = self.methods = {'ping', 'fail', 'not_found'}
        attrs = {method: guarded_method(method) for method in methods}
        attrs['_wrapped_methods'] = methods
        handler = self.handler = Mock()
        handler.ping.side_effect = lambda value: value
        handler.fail.side_effect = UnknownException()
        handler.not_found.side_effect = NotFound()
        handler.unknown.side_effect = UnknownException()
        cls = type('GuardedHandler', (BaseWrappedHandler,), attrs)
        self.guarded = cls(handler)
        super(TestGuardedMethod, self).setUp()

    def test_introspection(self):
        for method in self.methods:
            self.assertIn(method, vars(self.guarded))

    def test_call(self):
        value = object()
        self.assertIs(value, self.guarded.ping(value))
        self.assertTrue(self.handler.ping.called)

    def test_unwrapped_method(self):
        # unwrapped method not touched, check this
        with self.assertRaises(UnknownException):
            self.guarded.unknown()

    def test_wrapped_method(self):
        # ensure that thrift exceptions properly re-raised
        with self.assertRaises(NotFound):
            self.guarded.not_found()
        # ensure that unknown exceptions properly wrapped
        with self.assertRaises(TApplicationException):
            self.guarded.fail()


class TestHandlerMeta(TestCase):

    def test_wrapped_class(self):
        service_name = 'ThriftPool'
        attrs = dict(_handler_cls=Handler,
                     _service_name=service_name)
        cls = WrappedHandlerMeta('GuardedHandler', (object, ), attrs)
        self.assertIs(Handler, cls._handler_cls)
        self.assertIs(service_name, cls._service_name)
        methods = set(cls._wrapped_methods)
        self.assertTrue(methods)
        self.assertTrue(methods <= set(vars(Iface).keys()))
        for method in methods:
            self.assertIsInstance(getattr(cls, method), guarded_method)

    def test_wrong_class(self):
        service_name = 'ThriftPool'
        attrs = dict(_handler_cls=WrongHandler,
                     _service_name=service_name)
        with self.assertRaises(WrappingError):
            WrappedHandlerMeta('GuardedHandler', (object, ), attrs)

    def test_missing_attributes(self):
        service_name = 'ThriftPool'
        with self.assertRaises(WrappingError):
            WrappedHandlerMeta('GuardedHandler', (object, ),
                               dict(_handler_cls=Handler))
        with self.assertRaises(WrappingError):
            WrappedHandlerMeta('GuardedHandler', (object, ),
                               dict(_service_name=service_name))
