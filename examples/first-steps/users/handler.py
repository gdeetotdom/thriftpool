import random

from thriftpool.base import BaseHandler

from org.stubs.users import UserStorage
from org.stubs.users.ttypes import UserProfile


class Handler(BaseHandler, UserStorage.Iface):
    """Implement generated interface."""

    class options:
        name = 'UserStorage'
        processor = UserStorage.Processor
        port = 10005

    def retrieve(self, uid):
        some_name = random.choice(('Alice', 'Bob'))
        return UserProfile(uid=uid,
                           name=some_name)
