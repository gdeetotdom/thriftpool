import os
import tempfile
import uuid

__all__ = ['mk_temp_path']


def mk_temp_path(prefix=None):
    return os.path.join(tempfile.gettempdir(),
                        ".{0}{1}".format(prefix or '', uuid.uuid4().hex))
