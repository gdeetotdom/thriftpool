import os
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

__all__ = ['mk_temp_path', 'cpu_count', 'setproctitle']


def mk_temp_path(prefix=None):
    return os.path.join(tempfile.gettempdir(),
                        ".{0}{1}".format(prefix or '', uuid.uuid4().hex))
