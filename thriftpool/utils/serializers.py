from __future__ import absolute_import

import os
import cPickle as pickle
from struct import Struct, calcsize
from select import select


class StreamSerializer(object):
    """Helper to pass python objects over streams."""

    length_format = '!i'

    def __init__(self):
        self.length_struct = Struct(self.length_format)
        self.length = calcsize(self.length_format)

    @staticmethod
    def encode(obj):
        return pickle.dumps(obj)

    @staticmethod
    def decode(message):
        return pickle.loads(message)

    def encode_with_length(self, obj):
        """Encode object and prepend length to message."""
        message = self.encode(obj)
        return self.length_struct.pack(len(message)) + message

    def decode_from_stream(self, fd, timeout=5):
        """Read object from given stream and return it."""
        rlist, _, _ = select([fd], [], [], timeout)
        if not rlist:
            raise RuntimeError("Can't read object from {0!r}.".format(fd))
        message_length = self.length_struct.unpack(os.read(fd, self.length))[0]
        assert message_length > 0, 'wrong message length provided'
        return self.decode(os.read(fd, message_length))
