from __future__ import absolute_import

import sys

from billiard import freeze_support

from thriftpool.utils.logs import mlevel, LOG_LEVELS
from thriftpool.bin.base import BaseCommand, Option


class WorkerCommand(BaseCommand):
    """Start ThiftPool daemon."""

    options = (
        Option('--log-request', help='Log all incoming requests',
               action='store_true'),
        Option('-l', '--log-level',
               help='Logging level, choose between `DEBUG`,'
                    ' `INFO`, `WARNING`, `ERROR`, `CRITICAL`,'
                    ' or `FATAL`.',
               action='store', default='INFO'),
    )

    def run(self, *args, **options):
        try:
            self.app.config.LOGGING_LEVEL = mlevel(options['log_level'])
        except KeyError:
            self.die('Unknown level {0!r}. Please use one of {1}.'.format(
                        options['log_level'], '|'.join(LOG_LEVELS.keys())))
        self.app.config.LOG_REQUESTS = options.get('log_request', False)
        self.app.orchestrator.start()


def main():
    # Fix for setuptools generated scripts, so that it will
    # work with multiprocessing fork emulation.
    # (see multiprocessing.forking.get_preparation_data())
    if __name__ != '__main__':  # pragma: no cover
        sys.modules['__main__'] = sys.modules[__name__]
    freeze_support()

    WorkerCommand().execute()


if __name__ == '__main__':
    main()
