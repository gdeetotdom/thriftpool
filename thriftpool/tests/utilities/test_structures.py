from __future__ import absolute_import

from six import StringIO

from thriftpool.tests.utils import TestCase
from thriftpool.utils.structures import AttributeDict, AggregatedView, \
    DependencyGraph


class TestDependencyGraph(TestCase):

    def graph1(self):
        return DependencyGraph([
            ('A', []),
            ('B', []),
            ('C', ['A']),
            ('D', ['C', 'B']),
        ])

    def test_repr(self):
        self.assertTrue(repr(self.graph1()))

    def test_topsort(self):
        order = self.graph1().topsort()
        # C must start before D
        self.assertLess(order.index('C'), order.index('D'))
        # and B must start before D
        self.assertLess(order.index('B'), order.index('D'))
        # and A must start before C
        self.assertLess(order.index('A'), order.index('C'))

    def test_edges(self):
        self.assertItemsEqual(
            list(self.graph1().edges()),
            ['C', 'D'],
        )

    def test_items(self):
        self.assertDictEqual(
            dict(self.graph1().items()),
            {'A': [], 'B': [], 'C': ['A'], 'D': ['C', 'B']},
        )

    def test_to_dot(self):
        s = StringIO()
        self.graph1().to_dot(s)
        self.assertTrue(s.getvalue())


class TestAttributeDict(TestCase):

    def test_getattr__setattr(self):
        x = AttributeDict({'foo': 'bar'})
        self.assertEqual(x['foo'], 'bar')
        with self.assertRaises(AttributeError):
            x.bar
        x.bar = 'foo'
        self.assertEqual(x['bar'], 'foo')


class TestConfigurationView(TestCase):

    def setUp(self):
        view = self.view = AggregatedView({'changed_key': 1, 'both': 2})
        view.add_default({'default_key': 1, 'both': 1})

    def test_setdefault(self):
        self.assertEqual(self.view.setdefault('both', 36), 2)
        self.assertEqual(self.view.setdefault('new', 36), 36)

    def test_get(self):
        self.assertEqual(self.view.get('both'), 2)
        sp = object()
        self.assertIs(self.view.get('nonexisting', sp), sp)

    def test_update(self):
        changes = dict(self.view._changes)
        self.view.update(a=1, b=2, c=3)
        self.assertDictEqual(self.view._changes,
                             dict(changes, a=1, b=2, c=3))

    def test_contains(self):
        self.assertIn('changed_key', self.view)
        self.assertIn('default_key', self.view)
        self.assertNotIn('new', self.view)

    def test_repr(self):
        self.assertIn('changed_key', repr(self.view))
        self.assertIn('default_key', repr(self.view))

    def test_iter(self):
        expected = {'changed_key': 1,
                    'default_key': 1,
                    'both': 2}
        self.assertDictEqual(dict(self.view.items()), expected)
        self.assertItemsEqual(list(iter(self.view)),
                              list(expected.keys()))
        self.assertItemsEqual(list(self.view.keys()), list(expected.keys()))
        self.assertItemsEqual(list(self.view.values()),
                              list(expected.values()))
