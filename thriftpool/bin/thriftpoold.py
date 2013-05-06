from __future__ import absolute_import

import os
import sys
import socket

from thriftpool.utils.logs import mlevel, LOG_LEVELS, LEVELS
from thriftpool.utils.platforms import set_process_title
from thriftpool.bin.base import BaseCommand, Option


class ManagerCommand(BaseCommand):
    """Start ThiftPool daemon."""

    options = (
        Option('--log-request', help='Log all incoming requests',
               action='store_true'),
        Option('-c', '--concurrency', help='Set concurrency level',
               action='store', type=int),
        Option('-w', '--workers', help='Set workers count',
               action='store', type=int),
        Option('-k', '--worker-type', help='Set type of worker',
               action='store', type=str, choices=['sync']),
        Option('-l', '--log-level',
               help='Logging level', choices=LEVELS,
               action='store', default='INFO'),
        Option('-f', '--log-file', help='Specify log file',
               action='store'),
        Option('-p', '--pid-file', help='Specify path to PID file',
               action='store'),
        Option('-d', '--daemonize', help='Daemonize after start',
               action='store_true'),
        Option('-m', '--modules', help='Modules to load',
               action='store', type=str, nargs='*'),
        Option('--foreground', help='Don not detach from console',
               action='store_true'),
        Option('--endpoint', help='Which address tornado should listen?',
               action='store', type=str, nargs='*'),
    )

    def change_process_title(self, app):
        """Set process title."""
        set_process_title('[{0}@{1}]{2}'
                          .format(app.config.PROCESS_NAME,
                                  socket.gethostname(),
                                  ' '.join([''] + sys.argv[1:])))

    def run(self, *args, **options):
        app = self.app
        try:
            app.config.LOGGING_LEVEL = mlevel(options['log_level'])
        except KeyError:
            self.die('Unknown level {0!r}. Please use one of {1}.'
                     .format(options['log_level'],
                             '|'.join(LOG_LEVELS.keys())))

        normalize_path = lambda path: \
            os.path.abspath(os.path.expanduser(path)) \
            if path is not None else None

        pid_file = normalize_path(options.get('pid_file', None))
        log_file = normalize_path(options.get('log_file', None))

        app.config.LOG_REQUESTS = options.get('log_request', False)
        app.config.LOG_FILE = log_file

        if options['workers']:
            app.config.WORKERS = options['workers']
        if options['concurrency']:
            app.config.CONCURRENCY = options['concurrency']
        if options['worker_type']:
            app.config.WORKER_TYPE = options['worker_type']
        if options['modules']:
            modules = list(app.config.MODULES)
            modules.extend(options['modules'])
            app.config.MODULES = modules
        if options['endpoint']:
            modules = list(app.config.TORNADO_ENDPOINTS)
            modules.extend(options['endpoint'])
            app.config.TORNADO_ENDPOINTS = modules

        self.change_process_title(app)
        controller = app.ManagerController()
        daemon = app.Daemon(controller=controller,
                            pidfile=pid_file,
                            daemonize=options.get('daemonize', False),
                            foreground=options.get('foreground', False),
                            args=args)
        daemon.start()


def main():
    ManagerCommand().execute()


if __name__ == '__main__':
    main()
