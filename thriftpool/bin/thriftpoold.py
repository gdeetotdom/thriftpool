from __future__ import absolute_import

import os

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
        Option('-f', '--log-file', help='Specify log file',
               action='store'),
        Option('-p', '--pid-file', help='Specify path to PID file',
               action='store'),
        Option('-d', '--daemonize', help='Daemonize after start',
               action='store_true'),
        Option('--foreground', help='Don not detach from console',
               action='store_true'),
    )

    def run(self, *args, **options):
        try:
            self.app.config.LOGGING_LEVEL = mlevel(options['log_level'])
        except KeyError:
            self.die('Unknown level {0!r}. Please use one of {1}.'.format(
                        options['log_level'], '|'.join(LOG_LEVELS.keys())))

        normalize_path = lambda path: \
            os.path.abspath(os.path.expanduser(path)) \
            if path is not None else None

        pid_file = normalize_path(options.get('pid_file', None))
        log_file = normalize_path(options.get('log_file', None))

        self.app.config.LOG_REQUESTS = options.get('log_request', False)
        self.app.config.LOG_FILE = log_file

        worker = self.app.Worker(pidfile=pid_file,
                                 daemonize=options.get('daemonize', False),
                                 foreground=options.get('foreground', False),
                                 args=args)
        worker.start()


def main():
    WorkerCommand().execute()


if __name__ == '__main__':
    main()
