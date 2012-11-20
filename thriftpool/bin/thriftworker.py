from __future__ import absolute_import

import os
import sys
import struct
import cPickle
from select import select

from thriftpool.bin.base import BaseCommand


def read_app_from_fd(fd, timeout=5):
    """Read application from given stream and return it."""
    rlist, _, _ = select([fd], [], [], timeout)
    if not rlist:
        raise RuntimeError("Can't read app from {0!r}.".format(fd))
    length = struct.unpack('I', os.read(fd, 4))[0]
    assert length > 0, 'wrong message length provided'
    app = cPickle.loads(os.read(fd, length))
    return app


def reopen_streams():
    """Reopen streams here to prevent buffering."""
    sys.stdin = os.fdopen(sys.stdin.fileno(), 'r', 0)
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
    sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', 0)


class WorkerCommand(BaseCommand):
    """Start ThiftPool worker."""

    def run(self, *args, **options):
        stream_fd = sys.stderr.fileno() + 1
        app = read_app_from_fd(stream_fd)
        controller = app.WorkerController(stream_fd)
        controller.start()


def main():
    reopen_streams()
    WorkerCommand().execute()


if __name__ == '__main__':
    main()
