from __future__ import absolute_import

import os
import sys
import struct
import cPickle

from thriftpool.bin.base import BaseCommand


class WorkerCommand(BaseCommand):
    """Start ThiftPool worker."""

    def app_from_stdin(self):
        stream = sys.stdin
        length = struct.unpack('I', stream.read(4))[0]
        assert length > 0, 'wrong message length provided'
        app = cPickle.loads(stream.read(length))
        return app

    def reopen_streams(self):
        """Reopen streams here to prevent buffering."""
        sys.stdin = os.fdopen(0, 'r', 0)
        sys.stdout = os.fdopen(1, 'w', 0)
        sys.stderr = os.fdopen(2, 'w', 0)

    def run(self, *args, **options):
        self.reopen_streams()
        app = self.app_from_stdin()
        controller = app.WorkerController()
        controller.start()


def main():
    WorkerCommand().execute()


if __name__ == '__main__':
    main()
