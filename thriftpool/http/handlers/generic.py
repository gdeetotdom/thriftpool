from __future__ import absolute_import

from thriftpool import __version__

from .base import BaseHandler


class WelcomeHandler(BaseHandler):

    def get(self):
        self.preflight()
        self.write({"welcome": "thriftpool", "version": __version__})


class VersionHandler(BaseHandler):

    def get(self):
        self.preflight()
        self.write({"name": "thriftpool", "version": __version__})


class PingHandler(BaseHandler):

    def get(self):
        self.preflight()
        self.set_status(200)
        self.write("OK")
