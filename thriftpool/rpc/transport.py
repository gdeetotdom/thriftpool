from __future__ import absolute_import

import logging
import cPickle as pickle
from uuid import UUID, uuid4
from struct import Struct
from cStringIO import StringIO

from gaffer.events import EventEmitter

from thriftworker.utils.decorators import cached_property
from thriftworker.utils.loop import in_loop

logger = logging.getLogger(__name__)


class Proto(object):
    """Mixin that produce *encode* and *decode* methods. Each packet
    represented by simple structure:

        +----------+--------------------+-----------------+
        | Length   | Request id (UUID)  | Pickled object  |
        +==========+====================+=================+
        | 4 bytes  | 32 bytes           | undefined       |
        +----------+--------------------+-----------------+

    """

    @cached_property
    def _length_struct(self):
        """Pack and unpack length."""
        return Struct('I')

    def _prepend_length(self, data):
        """Prepend length to data."""
        return self._length_struct.pack(len(data)) + data

    def _encode(self, request_id, obj):
        """Convert given request to packet."""
        assert isinstance(request_id, UUID), 'wrong request id given'
        return self._prepend_length(request_id.hex + pickle.dumps(obj))

    def _split_length(self, data):
        """Return tuple of length and raw data."""
        assert len(data) >= 4, 'given buffer to small (length)'
        encoded_length, left_data = data[:4], data[4:]
        length = self._length_struct.unpack(encoded_length)[0]
        assert length > 0, 'wrong length provided'
        return (length, left_data)

    def _split_request_id(self, data):
        """Return tuple of request id and raw data."""
        assert len(data) >= 32, 'given buffer to small (request_id)'
        request_id, left_data = data[:32], data[32:]
        return (UUID(hex=request_id, version=4), left_data)

    def _decode_body(self, data):
        """Unpickle given data."""
        return pickle.loads(data)


class Receiver(Proto):
    """Receive request from channel."""

    WAIT_LENGTH = 1
    WAIT_PAYLOAD = 2

    def __init__(self, stream, emitter):
        self.stream = stream
        self.emitter = emitter
        self._buf = StringIO()
        self._state = self.WAIT_LENGTH
        self._received = self._length = 0
        super(Receiver, self).__init__()

    def _on_read(self, evtype, info):
        data = info['data']
        if self._state == self.WAIT_LENGTH:
            # Try to receive packet length here.
            self._length, data = self._split_length(data)
            self._state = self.WAIT_PAYLOAD
        if self._state == self.WAIT_PAYLOAD:
            # Write data to buffer.
            self._received += len(data)
            self._buf.write(data)
        if self._received >= self._length:
            data = self._buf.getvalue()
            data, left = data[:self._length], data[self._length:]
            self._on_received(data)
            self._buf = StringIO()
            self._received = self._length = 0
            self._state = self.WAIT_LENGTH
            if left:
                self._on_read(evtype, dict(data=left))

    def _on_received(self, data):
        request_id, data = self._split_request_id(data)
        obj = self._decode_body(data)
        self.emitter.publish("received", request_id=request_id, obj=obj)

    def start(self):
        self.stream.subscribe(self._on_read)

    def stop(self):
        self.stream.unsubscribe(self._on_read)


class Transmitter(Proto):
    """Write request to channel."""

    def __init__(self, stream, emitter):
        self.stream = stream
        self.emitter = emitter
        self._requests = {}
        super(Transmitter, self).__init__()

    def write(self, obj, callback=None, request_id=None):
        request_id = request_id or uuid4()
        if callback is not None:
            self._requests[request_id] = callback
        data = self._encode(request_id, obj)
        self.stream.write(data)

    def _on_received(self, evtype, request_id, obj):
        callback = self._requests.pop(request_id, None)
        if callback is not None:
            try:
                callback(obj)
            except Exception as exc:
                logger.exception(exc)

    def start(self):
        self.emitter.subscribe('received', self._on_received)

    def stop(self):
        self.emitter.unsubscribe('received', self._on_received)


class Transport(object):
    """Exchange messages on channel."""

    Receiver = Receiver
    Transmitter = Transmitter

    def __init__(self, loop, incoming, outgoing):
        self.loop = loop
        self._emitter = EventEmitter(loop)
        self._receiver = self.Receiver(incoming, self._emitter)
        self._transmitter = self.Transmitter(outgoing, self._emitter)

    def write(self, obj, callback=None, request_id=None):
        self._transmitter.write(obj, callback, request_id)

    def subscribe(self, listener):
        self._emitter.subscribe('received', listener)

    def unsubscribe(self, listener):
        self._emitter.unsubscribe('received', listener)

    def start(self):
        self._receiver.start()
        self._transmitter.start()

    def stop(self):
        self._transmitter.stop()
        self._receiver.stop()
        self._emitter.close()


class Consumer(Transport):
    """Pull commands from consumer, execute them and return result."""

    def __init__(self, loop, incoming, outgoing, handler):
        self.handler = handler
        super(Consumer, self).__init__(loop, incoming, outgoing)

    def _on_incoming(self, evtype, request_id, obj):
        method_name, args, kwargs = obj
        logger.debug('Execute method {0!r} with args {1!r} and kwargs {2!r}'
                     .format(method_name, args, kwargs))
        try:
            result = getattr(self.handler, method_name)(*args, **kwargs)
        except Exception as exc:
            logger.exception(exc)
            result = exc
        self.write(result, request_id=request_id)

    def start(self):
        super(Consumer, self).start()
        self.subscribe(self._on_incoming)

    def stop(self):
        self.unsubscribe(self._on_incoming)
        super(Consumer, self).stop()


class Producer(Transport):
    """Push commands to consumer."""

    def __init__(self, loop, incoming, outgoing):
        super(Producer, self).__init__(loop, incoming, outgoing)

    @in_loop
    def apply(self, method_name, callback=None, args=None, kwargs=None):
        """Enqueue new remote procedure call."""
        self.write((str(method_name), args or [], kwargs or {}), callback)
