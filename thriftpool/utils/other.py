from __future__ import absolute_import

import re

__all__ = ['rgetattr', 'camelcase_to_underscore', 'setproctitle']


try:
    from setproctitle import setproctitle
except ImportError:
    def setproctitle(title):
        return


def camelcase_to_underscore(s):
    """Convert CamelCase to under_score."""
    return str(re.sub('(((?<=[a-z])[A-Z])|([A-Z](?![A-Z]|$)))', '_\\1', s)
               .lower().strip('_'))


def rgetattr(obj, path):
    """Get nested attribute from object.

    :param obj: object
    :param path: path to attribute

    """
    return reduce(getattr, [obj] + path.split('.'))
