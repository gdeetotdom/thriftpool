from __future__ import absolute_import

import sys

from thriftpool.bin.base import BaseCommand
from thriftpool.utils.serializers import StreamSerializer


class Unbuffered(object):

   def __init__(self, stream):
       self.stream = stream

   def write(self, data):
       self.stream.write(data)
       self.stream.flush()

   def __getattr__(self, attr):
       return getattr(self.stream, attr)

   def __repr__(self):
       return repr(self.stream)


class WorkerCommand(BaseCommand):
    """Start ThiftPool worker."""

    def run(self, *args, **options):
        stream_fd = sys.stderr.fileno() + 1
        app = StreamSerializer().decode_from_stream(stream_fd)
        controller = app.WorkerController(stream_fd)
        controller.start()


def main():
    sys.stdout = Unbuffered(sys.stdout)
    sys.stderr = Unbuffered(sys.stderr)
    WorkerCommand().execute()


if __name__ == '__main__':
    main()
