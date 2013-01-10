"""Some base structures.

This file was copied and adapted from celery.

:copyright: (c) 2009 - 2012 by Ask Solem.
:license: BSD, see LICENSE for more details.

"""
from __future__ import absolute_import

from collections import defaultdict
import itertools

from six import iteritems, iterkeys

__all__ = ['DependencyGraph', 'AttributeDict', 'AggregatedView']


class DependencyGraph(object):
    """A directed acyclic graph of objects and their dependencies.

    Supports a robust topological sort
    to detect the order in which they must be handled.

    Takes an optional iterator of ``(obj, dependencies)``
    tuples to build the graph from.

    .. warning::

        Does not support cycle detection.

    """

    def __init__(self, it=None):
        self.adjacent = {}
        if it is not None:
            self.update(it)

    def add_arc(self, obj):
        """Add an object to the graph."""
        self.adjacent.setdefault(obj, [])

    def add_edge(self, A, B):
        """Add an edge from object ``A`` to object ``B``
        (``A`` depends on ``B``)."""
        self[A].append(B)

    def topsort(self):
        """Sort the graph topologically.

        :returns: a list of objects in the order
            in which they must be handled.

        """
        graph = DependencyGraph()
        components = self._tarjan72()

        NC = dict((node, component)
                  for component in components
                  for node in component)
        for component in components:
            graph.add_arc(component)
        for node in self:
            node_c = NC[node]
            for successor in self[node]:
                successor_c = NC[successor]
                if node_c != successor_c:
                    graph.add_edge(node_c, successor_c)
        return [t[0] for t in graph._khan62()]

    def valency_of(self, obj):
        """Returns the velency (degree) of a vertex in the graph."""
        try:
            l = [len(self[obj])]
        except KeyError:
            return 0
        for node in self[obj]:
            l.append(self.valency_of(node))
        return sum(l)

    def update(self, it):
        """Update the graph with data from a list
        of ``(obj, dependencies)`` tuples."""
        tups = list(it)
        for obj, _ in tups:
            self.add_arc(obj)
        for obj, deps in tups:
            for dep in deps:
                self.add_edge(obj, dep)

    def edges(self):
        """Returns generator that yields for all edges in the graph."""
        return (obj for obj, adj in self.iteritems() if adj)

    def _khan62(self):
        """Khans simple topological sort algorithm from '62

        See http://en.wikipedia.org/wiki/Topological_sorting

        """
        count = defaultdict(lambda: 0)
        result = []

        for node in self:
            for successor in self[node]:
                count[successor] += 1
        ready = [node for node in self if not count[node]]

        while ready:
            node = ready.pop()
            result.append(node)

            for successor in self[node]:
                count[successor] -= 1
                if count[successor] == 0:
                    ready.append(successor)
        result.reverse()
        return result

    def _tarjan72(self):
        """Tarjan's algorithm to find strongly connected components.

        See http://bit.ly/vIMv3h.

        """
        result, stack, low = [], [], {}

        def visit(node):
            if node in low:
                return
            num = len(low)
            low[node] = num
            stack_pos = len(stack)
            stack.append(node)

            for successor in self[node]:
                visit(successor)
                low[node] = min(low[node], low[successor])

            if num == low[node]:
                component = tuple(stack[stack_pos:])
                stack[stack_pos:] = []
                result.append(component)
                for item in component:
                    low[item] = len(self)

        for node in self:
            visit(node)

        return result

    def to_dot(self, fh, ws=" " * 4):
        """Convert the graph to DOT format.

        :param fh: A file, or a file-like object to write the graph to.

        """
        fh.write("digraph dependencies {\n")
        for obj, adjacent in self.iteritems():
            if not adjacent:
                fh.write(ws + '"%s"\n' % (obj,))
            for req in adjacent:
                fh.write(ws + '"%s" -> "%s"\n' % (obj, req))
        fh.write("}\n")

    def __iter__(self):
        return iterkeys(self.adjacent)

    def __getitem__(self, node):
        return self.adjacent[node]

    def __len__(self):
        return len(self.adjacent)

    def __contains__(self, obj):
        return obj in self.adjacent

    def _iterate_items(self):
        return iteritems(self.adjacent)
    items = iteritems = _iterate_items

    def __repr__(self):
        return '\n'.join(self.repr_node(N) for N in self)

    def repr_node(self, obj, level=1):
        output = ["%s(%s)" % (obj, self.valency_of(obj))]
        if obj in self:
            for other in self[obj]:
                d = "%s(%s)" % (other, self.valency_of(other))
                output.append('     ' * level + d)
                output.extend(self.repr_node(other, level + 1).split('\n')[1:])
        return '\n'.join(output)


class AttributeDictMixin(object):
    """Adds attribute access to mappings.

    `d.key -> d[key]`

    """

    def __getattr__(self, k):
        """`d.key -> d[key]`"""
        try:
            return self[k]
        except KeyError:
            raise AttributeError(
                "'%s' object has no attribute '%s'" % (type(self).__name__, k))

    def __setattr__(self, key, value):
        """`d[key] = value -> d.key = value`"""
        self[key] = value


class AttributeDict(dict, AttributeDictMixin):
    """Dict subclass with attribute access."""
    pass


class AggregatedView(AttributeDictMixin):
    """Combine multiple dictionary to one."""

    def __init__(self, d):
        changes = {}
        self.__dict__.update(_changes=changes,
                             _underlying_dicts=[changes, d])

    def add_default(self, d):
        self._underlying_dicts.insert(2, d)

    def __getitem__(self, key):
        for d in self._underlying_dicts:
            try:
                return d[key]
            except KeyError:
                pass
        raise KeyError(key)

    def __setitem__(self, key, value):
        self._changes[key] = value

    def __contains__(self, key):
        for d in self._underlying_dicts:
            if key in d:
                return True
        return False

    def __iter__(self):
        return iter(set(itertools.chain.from_iterable(
                        [self._changes] + self._underlying_dicts)))

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def setdefault(self, key, default):
        try:
            return self[key]
        except KeyError:
            self[key] = default
            return default

    def update(self, *args, **kwargs):
        return self._changes.update(*args, **kwargs)

    def items(self):
        return [(key, self[key]) for key in self]

    def values(self):
        return [self[key] for key in self]

    def keys(self):
        return list(self)

    def __repr__(self):
        return repr(dict(self.items()))
