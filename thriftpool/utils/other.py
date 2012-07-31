import os
import tempfile
import uuid

__all__ = ['mk_temp_path']


def mk_temp_path():
    return os.path.join(tempfile.gettempdir(),
                        ".{0}".format(uuid.uuid4().hex))
