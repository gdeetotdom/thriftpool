# cython: profile=True
cimport cython
from cpython cimport bool
from libcpp.string cimport string
import struct
from gevent.hub import get_hub
from gevent.socket import EAGAIN, error


cdef class SocketSource(object):
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

    def __cinit__(self):
        """We need to allocate std::string. Us it as buffer."""
        self.message = new string()
        self.len = 0
        self.status = WAIT_LEN

    def __dealloc__(self):
        del self.message

    def __init__(self, socket, callback):
        assert callable(callback)
        self.socket = socket._sock
        self.fileno = self.socket.fileno()
        self.callback = callback
        self.format = struct.Struct('!i')

        self.__setup_events()
        self.start_listen_read()

    cpdef __setup_events(self):
        loop = get_hub().loop
        MAXPRI = loop.MAXPRI
        io = loop.io

        self.__read_watcher = io(self.fileno, 1)
        self.__read_watcher.priority = MAXPRI
        self.__write_watcher = io(self.fileno, 2)
        self.__write_watcher.priority = MAXPRI

    @cython.profile(False)
    cdef inline void start_listen_read(self):
        """Start listen read events."""
        self.__read_watcher.start(self.on_readable)

    @cython.profile(False)
    cdef inline void stop_listen_read(self):
        """Stop listen read events."""
        self.__read_watcher.stop()

    @cython.profile(False)
    cdef inline void start_listen_write(self):
        """Start listen write events."""
        self.__write_watcher.start(self.on_writable)

    @cython.profile(False)
    cdef inline void stop_listen_write(self):
        """Stop listen write events."""
        self.__write_watcher.stop()

    @cython.profile(False)
    cdef inline bool is_writeable(self):
        "Returns True if connection should be added to write list of select."
        return self.status == SEND_ANSWER

    @cython.profile(False)
    cdef inline bool is_readable(self):
        "Returns True if connection should be added to read list of select."
        return self.status == WAIT_LEN or self.status == WAIT_MESSAGE

    @cython.profile(False)
    cdef inline bool is_closed(self):
        "Returns True if connection is closed."
        return self.status == CLOSED

    @cython.profile(False)
    cdef inline bool is_ready(self):
        "Returns True if connection is ready."
        return self.status == WAIT_PROCESS

    cdef inline bytes content(self):
        return self.message.c_str()[:self.message.size()]

    cdef inline void expunge(self, int sent):
        cdef string s
        s = self.message.substr(sent, self.message.size() - sent)
        self.message.assign(s)

    cdef inline _read_len(self):
        """Reads length of request.

        It's really paranoic routine and it may be replaced by
        self.socket.recv(4).

        """
        read = self.socket.recv(4 - self.message.size())
        cdef int read_length = len(read)

        if read_length == 0:
            # if we read 0 bytes and self.message is empty, it means client
            # close connection
            self.close()
            return

        # always set string length, otherwise it will be read until
        # null byte.
        self.message.append(<char *>read, read_length)

        if self.message.size() == 4:
            self.len, = self.format.unpack(self.content())
            assert self.len >= 0, "negative frame size, it seems client" \
                " doesn't use FramedTransport"
            assert self.len != 0, "empty frame, it's really strange"

            self.message.clear()
            self.status = WAIT_MESSAGE

    cdef read(self):
        """Reads data from stream and switch state."""
        cdef int read_length
        assert self.is_readable()

        if self.status == WAIT_LEN:
            self._read_len()
            # go back to the main loop here for simplicity instead of
            # falling through, even though there is a good chance that
            # the message is already available

        elif self.status == WAIT_MESSAGE:
            read = self.socket.recv(self.len - self.message.size())
            read_length = len(read)

            assert read_length > 0, "can't read frame from socket " \
                "(get %d of %d bytes)" % (self.message.size(), self.len)

            self.message.append(<char *>read, read_length)

            if self.message.size() == self.len:
                self.status = WAIT_PROCESS

    cdef write(self):
        """Writes data from socket and switch state."""
        assert self.is_writeable()

        sent = self.socket.send(self.content())

        if sent == self.message.size():
            self.status = WAIT_LEN
            self.message.clear()
            self.len = 0
        else:
            self.expunge(sent)

    cdef close(self):
        """Closes connection."""
        self.status = CLOSED
        self.stop_listen_read()
        self.stop_listen_write()
        self.socket.close()

    cpdef object ready(self, bool all_ok, object message):
        """The ready can switch Connection to three states:

            WAIT_LEN if request was oneway.
            SEND_ANSWER if request was processed in normal way.
            CLOSED if request throws unexpected exception.

        """
        assert self.is_ready()

        if not all_ok:
            self.close()
            return

        self.len = 0
        cdef int message_length = len(message)
        if message_length == 0:
            # it was a oneway request, do not write answer
            self.message.clear()
            self.status = WAIT_LEN
            self.start_listen_read()
        else:
            length = self.format.pack(message_length)
            self.message.assign(<char *>length, 4)
            self.message.append(<char *>message, message_length)
            self.status = SEND_ANSWER
            self.start_listen_write()

    cpdef on_readable(self):
        assert self.is_readable()
        try:
            while self.is_readable():
                self.read()
            if self.is_ready():
                self.stop_listen_read()
                self.callback(self.content())
        except error, e:
            if e.errno != EAGAIN:
                self.close()
                raise
        except:
            self.close()
            raise

    cpdef on_writable(self):
        assert self.is_writeable()
        try:
            while self.is_writeable():
                self.write()
            if self.is_readable():
                self.stop_listen_write()
                self.start_listen_read()
            elif self.is_closed():
                self.stop_listen_write()
        except error, e:
            if e.errno != EAGAIN:
                self.close()
                raise
        except:
            self.close()
            raise
