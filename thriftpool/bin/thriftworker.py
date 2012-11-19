from __future__ import absolute_import

import os
import sys
import struct
import cPickle
from select import select

from thriftpool.bin.base import BaseCommand


def read_app_from_stream(stream, timeout=5):
    """Read application from given stream and return it."""
    rlist, _, _ = select([stream], [], [], timeout)
    if not rlist:
        raise RuntimeError("Can't read app from {0!r}.".format(stream))
    length = struct.unpack('I', stream.read(4))[0]
    assert length > 0, 'wrong message length provided'
    app = cPickle.loads(stream.read(length))
    return app


def reopen_streams():
    """Reopen streams here to prevent buffering."""
    sys.stdin = os.fdopen(sys.stdin.fileno(), 'r', 0)
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
    sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', 0)


class WorkerCommand(BaseCommand):
    """Start ThiftPool worker."""

    def run(self, *args, **options):
        stream = os.fdopen(sys.stderr.fileno() + 1, 'w+', 0)
        app = read_app_from_stream(stream)
        controller = app.WorkerController(stream.fileno())
        controller.start()


def main():
    reopen_streams()
    WorkerCommand().execute()


if __name__ == '__main__':
    main()
