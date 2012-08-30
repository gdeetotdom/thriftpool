from __future__ import absolute_import

import sys

from billiard import freeze_support

from thriftpool.app.base import ThriftPool


def main():
    # Fix for setuptools generated scripts, so that it will
    # work with multiprocessing fork emulation.
    # (see multiprocessing.forking.get_preparation_data())
    if __name__ != '__main__':  # pragma: no cover
        sys.modules['__main__'] = sys.modules[__name__]
    freeze_support()

    app = ThriftPool()
    app.orchestrator.start()


if __name__ == '__main__':
    main()
