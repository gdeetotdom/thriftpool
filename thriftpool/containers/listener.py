from .base import ControllerContainer

__all__ = ['ListenerContainer']


class ListenerContainer(ControllerContainer):

    def create(self):
        return self.app.ListenerController()

    def listen_for(self, frontend, backend):
        print frontend, backend
