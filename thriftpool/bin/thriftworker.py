from __future__ import absolute_import

import os
import sys

from thriftpool.bin.base import BaseCommand
from thriftpool.utils.serializers import StreamSerializer


def reopen_streams():
    """Reopen streams here to prevent buffering."""
    sys.stdin = os.fdopen(sys.stdin.fileno(), 'r', 0)
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
    sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', 0)


class WorkerCommand(BaseCommand):
    """Start ThiftPool worker."""

    def run(self, *args, **options):
        stream_fd = sys.stderr.fileno() + 1
        app = StreamSerializer().decode_from_stream(stream_fd)
        controller = app.WorkerController(stream_fd)
        controller.start()


def main():
    reopen_streams()
    WorkerCommand().execute()


if __name__ == '__main__':
    main()
