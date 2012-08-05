try:
    from setproctitle import setproctitle
except ImportError:
    def setproctitle(title):
        pass

__all__ = ['setproctitle']
