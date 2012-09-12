from __future__ import absolute_import

import atexit
import warnings
import socket
import os

from thriftpool.utils.other import setproctitle
from thriftpool.utils.platforms import create_pidlock
from thriftpool.utils.functional import cached_property


class Worker(object):
    """Worker behavior."""

    app = None

    def __init__(self, pidfile=None):
        self.pidfile = pidfile
        self.pidlock = None
        atexit.register(self.on_exit)

    def change_process_titile(self):
        """Set process title."""
        setproctitle('[{0}@{1}]'.format(self.app.config.PROCESS_NAME,
                                        socket.gethostname()))

    @cached_property
    def orchestrator(self):
        return self.app.OrchestratorController()

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
        self.orchestrator.start()

    def on_exit(self):
        pass
