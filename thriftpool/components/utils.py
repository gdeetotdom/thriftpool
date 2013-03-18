"""Some useful tools for components."""
from __future__ import absolute_import

import logging

from thriftworker.utils.decorators import cached_property

from thriftpool.app import current_app
from thriftpool.exceptions import SystemTerminate

logger = logging.getLogger(__name__)


class Aborted(Exception):
    """Waiting was aborted."""


class Waiter(object):
    """Waiter primitive."""

    def __init__(self, timeout=None):
        self.timeout = timeout or 30
        self._aborted = False
        super(Waiter, self).__init__()

    @cached_property
    def _event(self):
        return current_app.env.RealEvent()

    def reset(self):
        """Reset waiter state."""
        self._aborted = False
        self._event.clear()

    def abort(self):
        """Abort initialization."""
        self._aborted = True
        self._event.set()

    def done(self):
        """Notify all that initialization done."""
        self._event.set()

    def wait(self):
        """Wait for initialization."""
        event = self._event
        try:
            event.wait(self.timeout)
            if self._aborted:
                raise Aborted('Waiter was aborted!')
            return event.is_set()
        finally:
            self.reset()

    def wait_or_terminate(self, msg=None):
        """Generate `SystemTerminate` in case of timeout or aborting."""
        try:
            if not self.wait():
                logger.error(msg or 'Timeout in waiter happened.')
                raise SystemTerminate()
        except Aborted:
            logger.info('Waiter aborted.')
            raise SystemTerminate()
