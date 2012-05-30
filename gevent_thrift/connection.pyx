# cython: profile=True
from gevent import socket
import logging
import struct
from libcpp.string cimport string
cimport cython
from cpython cimport bool
from gevent.hub import get_hub
from gevent.event import Event


cdef enum ConnectionStates:
    WAIT_LEN = 0
    WAIT_MESSAGE = 1
    WAIT_PROCESS = 2
    SEND_ANSWER = 3
    CLOSED = 4


def socket_exception(func):
    "Decorator close object on socket.error."
    def inner(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except socket.error:
            self.close()
    return inner


@cython.final
cdef class Connection(object):
    """Basic class is represented connection.

    It can be in state:
        WAIT_LEN --- connection is reading request len.
        WAIT_MESSAGE --- connection is reading request.
        WAIT_PROCESS --- connection has just read whole request and 
            waits for call ready routine.
        SEND_ANSWER --- connection is sending answer string (including length
            of answer).
        CLOSED --- socket was closed and connection should be deleted.
    """

    cdef object socket
    cdef object format
    cdef ConnectionStates status
    cdef size_t len
    cdef string *message
    cdef object event
    cdef object read_watcher
    cdef object write_watcher

    def __cinit__(self):
        self.message = new string()
        self.len = 0
        self.status = WAIT_LEN

    def __init__(self, client_socket):
        self.socket = client_socket
        self.format = struct.Struct('!i')
        self.event = Event()

        loop = get_hub().loop
        self.read_watcher = loop.io(self.socket.fileno(), 1)
        self.write_watcher = loop.io(self.socket.fileno(), 2)
        self.read_watcher.priority = loop.MAXPRI
        self.write_watcher.priority = loop.MAXPRI

        self.start_listen_read()

    def __dealloc__(self):
        del self.message

    cdef inline void _read_len(self):
        """Reads length of request.

        It's really paranoic routine and it may be replaced by
        self.socket.recv(4)."""
        read = self.socket.recv(4 - self.message.size())
        cdef int read_length = len(read)
        if read_length == 0:
            # if we read 0 bytes and self.message is empty, it means client close 
            # connection
            if self.message.size() != 0:
                logging.error("can't read frame size from socket")
            self.close()
            return
        self.message.append(<char *>read, read_length)
        if self.message.size() == 4:
            self.len, = self.format.unpack(self.content())
            if self.len < 0:
                logging.error("negative frame size, it seems client"\
                    " doesn't use FramedTransport")
                self.close()
            elif self.len == 0:
                logging.error("empty frame, it's really strange")
                self.close()
            else:
                self.message.clear()
                self.status = WAIT_MESSAGE

    cdef void read(self):
        """Reads data from stream and switch state."""
        cdef int read_length = 0
        assert self.is_readable()
        if self.status == WAIT_LEN:
            self._read_len()
            # go back to the main loop here for simplicity instead of
            # falling through, even though there is a good chance that
            # the message is already available
        elif self.status == WAIT_MESSAGE:
            read = self.socket.recv(self.len - self.message.size())
            read_length = len(read)
            if read_length == 0:
                logging.error("can't read frame from socket (get %d of %d bytes)" %
                    (self.message.size(), self.len))
                self.close()
                return
            self.message.append(<char *>read, read_length)
            if self.message.size() == self.len:
                self.status = WAIT_PROCESS

    cdef void write(self):
        """Writes data from socket and switch state."""
        cdef string s
        assert self.is_writeable()
        sent = self.socket.send(self.content())
        if sent == self.message.size():
            self.status = WAIT_LEN
            self.message.clear()
            self.len = 0
        else:
            s = self.message.substr(sent, self.message.size() - sent)
            self.message.assign(s)

    cdef void ready(self, all_ok, message):
        """Callback function for switching state and waking up main thread.

        This function is the only function witch can be called asynchronous.

        The ready can switch Connection to three states:
            WAIT_LEN if request was oneway.
            SEND_ANSWER if request was processed in normal way.
            CLOSED if request throws unexpected exception.

        The one wakes up main thread.
        """
        assert self.is_ready()
        if not all_ok:
            self.close()
            return
        self.len = 0
        if len(message) == 0:
            # it was a oneway request, do not write answer
            self.message.clear()
            self.status = WAIT_LEN
        else:
            reply = self.format.pack(len(message)) + message
            self.message.assign(<char *>reply, len(reply))
            self.status = SEND_ANSWER

    cpdef close(self):
        "Closes connection"
        self.status = CLOSED
        self.stop_listen_read()
        self.stop_listen_write()
        self.socket.close()

    @cython.profile(False)
    cpdef inline bool is_writeable(self):
        "Returns True if connection should be added to write list of select."
        return self.status == SEND_ANSWER

    @cython.profile(False)
    cpdef inline bool is_readable(self):
        "Returns True if connection should be added to read list of select."
        return self.status == WAIT_LEN or self.status == WAIT_MESSAGE

    @cython.profile(False)
    cpdef inline bool is_closed(self):
        "Returns True if connection is closed."
        return self.status == CLOSED

    @cython.profile(False)
    cpdef inline bool is_ready(self):
        "Returns True if connection is ready."
        return self.status == WAIT_PROCESS

    cpdef inline bytes content(self):
        cdef bytes s = self.message.c_str()[:self.message.size()]
        return s

    cdef inline void start_listen_read(self):
        self.read_watcher.start(self.on_readable)

    cdef inline void start_listen_write(self):
        self.write_watcher.start(self.on_writable)

    cdef inline void stop_listen_read(self):
        self.read_watcher.stop()

    cdef inline void stop_listen_write(self):
        self.write_watcher.stop()

    cpdef on_readable(self):
        assert self.is_readable()
        try:
            self.read()
            if self.is_ready() or self.is_closed():
                self.stop_listen_read()
                self.event.set()
            else:
                assert self.is_readable()
        except:
            self.close()
            self.event.set()
            logging.error("invalid state after read")

    cpdef on_writable(self):
        assert self.is_writeable()
        try:
            self.write()
            if self.is_readable():
                self.stop_listen_write()
                self.start_listen_read()
            elif self.is_closed():
                self.stop_listen_write()
            else:
                assert self.is_writeable()
        except:
            self.close()
            logging.error("invalid state after write")

    cpdef get_request(self):
        self.event.wait()
        self.event.clear()
        assert self.is_ready() or self.is_closed()
        return self.content()

    cpdef set_reply(self, content, is_successed=True):
        assert self.is_ready()
        self.ready(is_successed, content)
        if self.is_writeable():
            self.start_listen_write()
        elif self.is_readable():
            self.start_listen_read()
        else:
            self.close()
