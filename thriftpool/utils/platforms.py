from __future__ import absolute_import

import os
import errno
import atexit
import sys
import resource
from contextlib import contextmanager

try:
    import setproctitle
except ImportError:
    setproctitle_exists = False
else:
    setproctitle_exists = True


EX_OK = getattr(os, 'EX_OK', 0)
EX_FAILURE = 1
EX_UNAVAILABLE = getattr(os, 'EX_UNAVAILABLE', 69)
EX_USAGE = getattr(os, 'EX_USAGE', 64)

DAEMON_UMASK = 0
DAEMON_WORKDIR = '/'


def set_process_title(name):
    """Change process title."""
    if not setproctitle_exists:
        return
    setproctitle.setproctitle(name)


def fileno(f):
    try:
        return f.fileno()
    except AttributeError:
        return f


def get_fdmax(default=None):
    """Returns the maximum number of open file descriptors
    on this system.

    :keyword default: Value returned if there's no file
                      descriptor limit.

    """
    fdmax = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    if fdmax == resource.RLIM_INFINITY:
        return default
    return fdmax


@contextmanager
def ignore_EBADF():
    try:
        yield
    except OSError as exc:
        if exc.errno != errno.EBADF:
            raise


class LockFailed(Exception):
    pass


class PIDLock(object):
    """Create PID lock and work with it as with resource."""

    FLAGS = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    MODE = ((os.R_OK | os.W_OK) << 6) | ((os.R_OK) << 3) | ((os.R_OK))

    def __init__(self, path):
        self.path = os.path.abspath(path)

    def read(self):
        """Reads and returns the writed PID lock."""
        try:
            fh = open(self.path, 'r')
        except IOError as exc:
            if exc.errno == errno.ENOENT:
                return
            raise

        try:
            line = fh.readline()
            if line.strip() == line:  # must contain '\n'
                raise ValueError(
                    'Partial or invalid PID lock {0.path}'.format(self))
        finally:
            fh.close()

        try:
            return int(line.strip())
        except ValueError:
            raise ValueError('PID lock {0.path} invalid.'.format(self))

    def write(self, pid):
        """Write given PID to lock."""
        fd = os.open(self.path, self.FLAGS, self.MODE)
        fh = os.fdopen(fd, 'w')
        try:
            fh.write('{0}\n'.format(pid))
            # flush and sync so that the re-read below works.
            fh.flush()
            try:
                os.fsync(fd)
            except AttributeError:
                pass
        finally:
            fh.close()

        # Check that PID wasn't change.
        if self.read() != pid:
            raise LockFailed('PID lock changed!')

    def remove(self):
        """Remove PID lock if exists."""
        try:
            os.unlink(self.path)
        except OSError as exc:
            if exc.errno == errno.ENOENT:
                return
            raise

    def exists(self):
        """Returns True if the PID lock exists."""
        return os.path.exists(self.path)

    @staticmethod
    def process_exists(pid):
        """Check that process exists."""
        try:
            os.kill(pid, 0)
        except os.error as exc:
            if exc.errno == errno.ESRCH:
                return False
        return True

    def maybe_remove(self):
        """Remove existed PID lock if we can."""
        if not self.exists():
            # No PID exists, return.
            return

        pid = self.read()
        if pid is None:
            # No PID found.
            return

        if self.process_exists(pid):
            raise LockFailed('PID lock exists.')

        self.remove()

    def acquire(self):
        """Try to write PID lock."""
        self.maybe_remove()
        self.write(os.getpid())

    def release(self, *args):
        """Try to remove PID lock."""
        self.remove()


def create_pidlock(pidfile):
    """Create PID lock, exit if fail."""
    pid = PIDLock(pidfile)
    try:
        pid.acquire()
    except LockFailed:
        raise SystemExit("Error: PID file ({0}) exists.".format(pidfile))
    atexit.register(pid.release)
    return pid


class Daemon(object):
    """Fork and close needed resources."""

    _is_open = False
    workdir = DAEMON_WORKDIR
    umask = DAEMON_UMASK

    def __init__(self, fake=False, excluded_fds=None):
        self.fake = fake
        self.standart_fds = (sys.stdin, sys.stdout, sys.stderr)
        self.excluded_fds = tuple(excluded_fds or [])

    @property
    def preserved_fds(self):
        return self.standart_fds + self.excluded_fds

    def redirect_to_null(self, fd):
        if fd:
            dest = os.open(os.devnull, os.O_RDWR)
            os.dup2(dest, fd)

    def _detach(self):
        if os.fork():
            os._exit(0)
        os.setsid()

        if os.fork():
            os._exit(0)
        return self

    def open(self):
        if not self._is_open:
            if not self.fake:
                self._detach()

            os.chdir(self.workdir)
            os.umask(self.umask)

            preserve = [fileno(f) for f in self.preserved_fds if fileno(f)]
            for fd in reversed(range(get_fdmax(default=2048))):
                if fd not in preserve:
                    with ignore_EBADF():
                        os.close(fd)

            for fd in self.standart_fds:
                self.redirect_to_null(fileno(fd))

            self._is_open = True

    def close(self, *args):
        if self._is_open:
            self._is_open = False


def daemonize(fake=False, excluded_fds=None):
    """Try to start daemon."""
    daemon = Daemon(fake, excluded_fds)
    daemon.open()
    atexit.register(daemon.close)
    return daemon
