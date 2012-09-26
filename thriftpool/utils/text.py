from __future__ import absolute_import


def indent(t, indent=0):
    """Indent text."""
    return '\n'.join(' ' * indent + p for p in t.split('\n'))
