from __future__ import absolute_import

import time
from threading import Thread

from thriftpool.tests.utils import TestCase
from thriftpool.utils import local


class LocalTestCase(TestCase):

    def test_basic_local(self):
        l = local.Local()
        l.foo = 0
        values = []

        def value_setter(idx):
            time.sleep(0.01 * idx)
            l.foo = idx
            time.sleep(0.02)
            values.append(l.foo)

        threads = [Thread(target=value_setter, args=(x,))
                   for x in [1, 2, 3]]
        for thread in threads:
            thread.start()
        time.sleep(0.2)
        self.assertEqual(sorted(values), [1, 2, 3])

        def delfoo():
            del l.foo

        delfoo()
        with self.assertRaises(AttributeError):
            l.foo()
        with self.assertRaises(AttributeError):
            delfoo()

        local.release_local(l)

    def test_local_release(self):
        loc = local.Local()
        loc.foo = 42
        local.release_local(loc)
        self.assertFalse(hasattr(loc, 'foo'))

        ls = local.LocalStack()
        ls.push(42)
        local.release_local(ls)
        self.assertIsNone(ls.top)

    def test_local_proxy(self):
        foo = []
        ls = local.LocalProxy(lambda: foo)
        ls.append(42)
        ls.append(23)
        ls[1:] = [1, 2, 3]
        self.assertEqual(foo, [42, 1, 2, 3])
        self.assertEqual(repr(foo), repr(ls))
        self.assertEqual(foo[0], 42)
        foo += [1]
        self.assertEqual(list(foo), [42, 1, 2, 3, 1])

    def test_local_stack(self):
        ident = local.get_ident()

        ls = local.LocalStack()
        self.assertNotIn(ident, ls._local.__storage__)
        self.assertIsNone(ls.top)
        ls.push(42)
        self.assertIn(ident, ls._local.__storage__)
        self.assertEqual(ls.top, 42)
        ls.push(23)
        self.assertEqual(ls.top, 23)
        ls.pop()
        self.assertEqual(ls.top, 42)
        ls.pop()
        self.assertIsNone(ls.top)
        self.assertIsNone(ls.pop())
        self.assertIsNone(ls.pop())

        proxy = ls()
        ls.push([1, 2])
        self.assertEqual(proxy, [1, 2])
        ls.push((1, 2))
        self.assertEqual(proxy, (1, 2))
        ls.pop()
        ls.pop()
        self.assertEqual(repr(proxy), '<LocalProxy unbound>')

        self.assertNotIn(ident, ls._local.__storage__)

    def test_local_proxies_with_callables(self):
        foo = 42
        ls = local.LocalProxy(lambda: foo)
        self.assertEqual(ls, 42)
        foo = [23]
        ls.append(42)
        self.assertEqual(ls, [23, 42])
        self.assertEqual(foo, [23, 42])
