"""Specify interface for all concurrency realizations."""
from zope.interface import Interface

__all__ = ['IPoolController']


class IPoolController(Interface):
    """All implementation of this interface provide control over the pool
    of workers.

    """

    def start(self):
        """Start registered workers."""

    def stop(self):
        """Gracephully stop pull of workers."""

    def register(self, controller):
        """Register new controller. Start it in separate worker."""
