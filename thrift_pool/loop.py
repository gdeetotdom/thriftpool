from gevent.greenlet import Greenlet


class IOLoop(Greenlet):
    def __init__(self):
        Greenlet.__init__(self)

    def _run(self):
        pass
