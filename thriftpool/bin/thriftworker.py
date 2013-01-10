from __future__ import absolute_import

import sys

from thriftpool.bin.base import BaseCommand
from thriftpool.utils.serializers import StreamSerializer


class WorkerCommand(BaseCommand):
    """Start ThiftPool worker."""

    def run(self, *args, **options):
        stream_fd = sys.stderr.fileno() + 1
        app = StreamSerializer().decode_from_stream(stream_fd)
        controller = app.WorkerController(stream_fd)
        controller.start()


def main():
    WorkerCommand().execute()


if __name__ == '__main__':
    main()
