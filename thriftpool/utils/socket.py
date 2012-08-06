import pyev
import zmq

__all__ = ['Socket']


class Socket(object):

    def __init__(self, hub, context, socket_type):
        self._hub = hub
        self._context = context
        self._socket = self._context.socket(socket_type)
        self.__watcher = self.__writable = self.__readable = None
        self.__setup_events()

    def __setup_events(self):
        self.__writable = self._hub.Waiter()
        self.__readable = self._hub.Waiter()
        self.__watcher = self._hub.IO(self.fileno, pyev.EV_READ)
        self.__watcher.start(self.__state_changed)

    def __state_changed(self):
        try:
            if self._socket.closed:
                # if the socket has entered a close state resume any waiting greenlets
                self.__writable.switch()
                self.__readable.switch()
                return
            events = self._socket.getsockopt(zmq.EVENTS)
        except zmq.ZMQError, exc:
            self.__writable.throw(exc)
            self.__readable.throw(exc)
        else:
            if events & zmq.POLLOUT:
                self.__writable.switch()
            if events & zmq.POLLIN:
                self.__readable.switch()

    def __wait_write(self):
        self.__writable = self._hub.Waiter()
        self.__writable.get()

    def __wait_read(self):
        self.__readable = self._hub.Waiter()
        self.__readable.get()

    @property
    def fileno(self):
        return self._socket.fd

    def connect(self, endpoint):
        self._socket.connect(endpoint)

    def bind(self, endpoint):
        self._socket.bind(endpoint)

    def send(self, data, flags=0):
        # ensure the zmq.NOBLOCK flag is part of flags
        flags = flags | zmq.NOBLOCK
        while True:
            # Attempt to complete this operation indefinitely, blocking the current greenlet
            try:
                # attempt the actual call
                return self._socket.send(data, flags)
            except zmq.ZMQError, e:
                # if the raised ZMQError is not EAGAIN, reraise
                if e.errno != zmq.EAGAIN:
                    raise
            # defer to the event loop until we're notified the socket is writable
            self.__wait_write()

    def recv(self):
        while True:
            try:
                return self._socket.recv(zmq.NOBLOCK)
            except zmq.ZMQError, e:
                if e.errno != zmq.EAGAIN:
                    raise
            self.__wait_read()

    def send_multipart(self, msg_parts):
        for msg in msg_parts[:-1]:
            self.send(msg, zmq.SNDMORE)
        # Send the last part without the extra SNDMORE flag.
        return self.send(msg_parts[-1])

    def recv_multipart(self):
        parts = [self.recv()]
        # have first part already, only loop while more to receive
        while self._socket.getsockopt(zmq.RCVMORE):
            part = self.recv()
            parts.append(part)
        return parts

    def close(self):
        if not self._socket.closed and self.__watcher is not None:
            self.__watcher.stop()
        self._socket.close()
