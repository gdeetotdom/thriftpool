"""Some useful tools for components."""
from __future__ import absolute_import

import logging

from thriftworker.utils.waiter import Waiter as BaseWaiter

from thriftpool.exceptions import SystemTerminate

logger = logging.getLogger(__name__)


class Aborted(Exception):
    """Waiting was aborted."""


class Waiter(BaseWaiter):
    """Waiter primitive."""

    def wait_or_terminate(self, msg=None):
        """Generate `SystemTerminate` in case of timeout or aborting."""
        try:
            if not self.wait():
                logger.error(msg or 'Timeout in waiter happened.')
                raise SystemTerminate()
        except Aborted:
            logger.info('Waiter aborted.')
            raise SystemTerminate()
