from __future__ import absolute_import

__all__ = ['SystemTerminate', 'RegistrationError']


class SystemTerminate(SystemExit):
    """Throw to terminate program."""


class RegistrationError(Exception):
    """Error happened on handler registration."""


class WrappingError(Exception):
    """Can't wrap given class."""
