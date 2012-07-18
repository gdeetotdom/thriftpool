

class Proxy(object):
    """Proxy handler."""

    app = None

    def __init__(self, ident):
        self.__client = self.app.Client(ident)

    def __getattr__(self, name):
        client = self.__client

        def inner(*args, **kwargs):
            request = {'method': name, 'args': args, 'kwargs': kwargs}
            client.send_reply(request)
            response = client.read_request()

            if 'result' in response:
                return response['result']
            elif 'exc_type' in response and 'exc_state' in response:
                exc = response['exc_type']()
                exc.__dict__.update(response['exc_state'])
                raise exc
            else:
                raise AssertionError('Wrong response')

        inner.__name__ = name
        return inner
