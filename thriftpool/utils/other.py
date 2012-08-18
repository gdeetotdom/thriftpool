import os
import re
import tempfile
import uuid

try:
    from billiard import cpu_count
except ImportError:
    cpu_count = lambda: 1

try:
    from setproctitle import setproctitle
except ImportError:
    def setproctitle(title):
        pass

__all__ = ['mk_temp_path', 'cpu_count', 'setproctitle',
           'camelcase_to_underscore']


def mk_temp_path(prefix=None):
    return os.path.join(tempfile.gettempdir(),
                        ".{0}{1}".format(prefix or '', uuid.uuid4().hex))


def camelcase_to_underscore(s):
    """Convert CamelCase to under_score."""
    return str(re.sub('(((?<=[a-z])[A-Z])|([A-Z](?![A-Z]|$)))', '_\\1', s)
               .lower().strip('_'))
