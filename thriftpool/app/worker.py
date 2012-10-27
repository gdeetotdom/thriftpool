from __future__ import absolute_import

import atexit
import warnings
import socket
import os

from thriftworker.utils.decorators import cached_property

from thriftpool.utils.other import setproctitle
from thriftpool.utils.platforms import create_pidlock, daemonize
from thriftpool.signals import collect_excluded_fds


class Worker(object):
    """Worker behavior."""

    app = None

    def __init__(self, pidfile=None, daemonize=False, foreground=False,
                 args=None):
        self.pidfile = pidfile
        self.pidlock = None
        self.daemonize = daemonize
        self.foreground = foreground
        self.daemon = None
        self.args = list(args or [])
        atexit.register(self.on_exit)

    def change_process_titile(self):
        """Set process title."""
        setproctitle('[{0}@{1}]{2}'.format(self.app.config.PROCESS_NAME,
                                           socket.gethostname(),
                                           ' '.join([''] + self.args)))

    @cached_property
    def controller(self):
        return self.app.WorkerController()

    def on_start(self):
        if getattr(os, 'getuid', None) and os.getuid() == 0:
            warnings.warn(RuntimeWarning(
                'Running thriftpoold with superuser privileges is discouraged!'))
        self.change_process_titile()

    def start(self):
        """Start new worker."""
        self.on_start()
        if self.pidfile is not None:
            self.pidlock = create_pidlock(self.pidfile)
        if self.daemonize:
            receivers = collect_excluded_fds.send(sender=self)
            excluded = [receiver[1] for receiver in receivers if receiver[1]]
            excluded = [item for sublist in excluded for item in sublist]
            self.daemon = daemonize(self.foreground, excluded_fds=excluded)
        self.controller.start()

    def on_exit(self):
        pass
