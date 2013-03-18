"""Base request handler."""
from __future__ import absolute_import

from tornado.web import RequestHandler, asynchronous

from thriftpool.app import current_app


ACCESS_CONTROL_HEADERS = [
    'X-Requested-With',
    'X-HTTP-Method-Override',
    'Content-Type',
    'Accept',
    'Authorization'
]

CORS_HEADERS = {
    'Access-Control-Allow-Methods': 'POST, GET, PUT, DELETE, OPTIONS',
    'Access-Control-Max-Age': '86400',  # 24 hours
    'Access-Control-Allow-Headers': ", ".join(ACCESS_CONTROL_HEADERS),
    'Access-Control-Allow-Credentials': 'true',
}


class BaseHandler(RequestHandler):

    @property
    def processes(self):
        return self.settings.get('processes')

    @asynchronous
    def options(self, *args, **kwargs):
        self.preflight()
        self.set_status(204)
        self.finish()

    def preflight(self):
        origin = self.request.headers.get('Origin', '*')

        if origin == 'null':
            origin = '*'

        self.set_header('Access-Control-Allow-Origin', origin)
        for k, v in CORS_HEADERS.items():
            self.set_header(k, v)

    def _execute(self, *args, **kwargs):
        execute = super(BaseHandler, self)._execute
        current_app.hub.spawn(execute, *args, **kwargs)
