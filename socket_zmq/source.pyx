cimport cython
from logging import getLogger
from pyev import EV_READ, EV_WRITE, EV_ERROR
from struct import unpack_from, pack, calcsize
import _socket
import errno
from socket_zmq.server cimport SinkPool
from socket_zmq.base cimport BaseSocket
from socket_zmq.sink cimport ZMQSink
from cpython cimport array

logger = getLogger(__name__)

NONBLOCKING = (errno.EAGAIN, errno.EWOULDBLOCK)
LENGTH_FORMAT = '!i'
LENGTH_SIZE = calcsize(LENGTH_FORMAT)
BUFFER_SIZE = 4096


cdef inline object allocate_buffer(Py_ssize_t size):
    """Create new style python buffer of given size."""
    return PyMemoryView_FromObject(
                        PyByteArray_FromStringAndSize(NULL, size))


cdef class SocketSource(BaseSocket):
    """Basic class is represented connection.

    It can be in state:
        WAIT_LEN --- connection is reading request length.
        WAIT_MESSAGE --- connection is reading request.
        WAIT_PROCESS --- connection has just read whole request and
            waits for call ready routine.
        SEND_ANSWER --- connection is sending answer string (including length
            of answer).
        CLOSED --- socket was closed and connection should be deleted.

    """

    def __init__(self, SinkPool pool, object loop, object socket,
                 object on_close):
        self.sent_bytes = self.recv_bytes = self.len = 0
        self.buffer = array.array("c")
        self.resize(BUFFER_SIZE)
        self.status = WAIT_LEN
        self.on_close = on_close
        self.socket = socket
        self.pool = pool
        self.sink = self.pool.get()
        BaseSocket.__init__(self, loop, self.socket.fileno())

    cdef inline void resize(self, Py_ssize_t size):
        cdef array.array[char] a = self.buffer.base
        array.resize_smart(a, size)
        self.buffer = a

    @cython.profile(False)
    cdef inline bint is_writeable(self):
        """Returns ``True`` if source is writable."""
        return self.status == SEND_ANSWER

    @cython.profile(False)
    cdef inline bint is_readable(self):
        """Returns ``True`` if source is readable."""
        return self.status == WAIT_LEN or self.status == WAIT_MESSAGE

    @cython.profile(False)
    cdef inline bint is_closed(self):
        """Returns ``True`` if source is closed."""
        return self.status == CLOSED

    @cython.profile(False)
    cdef inline bint is_ready(self):
        """Returns ``True`` if source is ready."""
        return self.status == WAIT_PROCESS

    @cython.locals(received=cython.int, message_length=cython.int)
    cdef inline read_length(self):
        """Reads length of request."""
        received = self.socket.recv_into(self.buffer,
                                         len(self.buffer))

        if received == 0:
            # if we read 0 bytes and message is empty, it means client
            # close connection
            self.close()
            return 0

        assert received >= LENGTH_SIZE, "message length can't be read"
        message_length = unpack_from(LENGTH_FORMAT,
                                     self.buffer.base[0:LENGTH_SIZE])[0]
        assert message_length > 0, "negative or empty frame size, it seems" \
                                   " client doesn't use FramedTransport"

        self.len = message_length + LENGTH_SIZE
        if len(self.buffer) < self.len:
            self.resize(self.len)

        self.status = WAIT_MESSAGE

        return received

    @cython.locals(readed=cython.int)
    cdef inline read(self):
        """Reads data from stream and switch state."""
        assert self.is_readable(), 'socket in non-readable state'
        readed = 0

        if self.status == WAIT_LEN:
            readed = self.read_length()
            if self.is_closed():
                return

        elif self.status == WAIT_MESSAGE:
            readed = self.socket.recv_into(self.buffer[self.recv_bytes:],
                                           self.len - self.recv_bytes)

        assert readed > 0, "can't read frame from socket"

        self.recv_bytes += readed
        if self.recv_bytes == self.len:
            self.recv_bytes = 0
            self.status = WAIT_PROCESS

    cdef inline write(self):
        """Writes data from socket and switch state."""
        assert self.is_writeable(), 'socket in non writable state'

        self.sent_bytes += self.socket.send(self.buffer[self.sent_bytes:self.len])

        if self.sent_bytes == self.len:
            self.status = WAIT_LEN
            self.len = 0
            self.sent_bytes = 0

    cpdef close(self):
        """Closes connection."""
        assert not self.is_closed(), 'socket already closed'
        self.status = CLOSED
        self.socket.close()
        if self.sink.is_ready():
            self.pool.put(self.sink)
        elif not self.sink.is_closed():
            self.sink.close()
        self.sink = None
        self.on_close(self)
        self.on_close = None
        self.buffer = None
        BaseSocket.close(self)

    @cython.locals(message_length=cython.int, response=array.array)
    cpdef ready(self, object all_ok, object message):
        """The ready can switch Connection to three states:

            WAIT_LEN if request was oneway.
            SEND_ANSWER if request was processed in normal way.
            CLOSED if request throws unexpected exception.

        """
        assert self.is_ready(), 'socket is not ready'

        if not all_ok:
            self.close()
            return

        message_length = len(message)
        if message_length == 0:
            # it was a oneway request, do not write answer
            self.status = WAIT_LEN
        else:
            self.resize(0)
            s = pack(LENGTH_FORMAT, message_length)
            array.extend_buffer(self.buffer.base, s, LENGTH_SIZE)
            array.extend_buffer(self.buffer.base, message, message_length)
            self.buffer = self.buffer.base
            message_length += LENGTH_SIZE
            self.status = SEND_ANSWER
            self.wait_writable()

        self.len = message_length

    cpdef cb_io(self, object watcher, object revents):
        if revents & EV_ERROR:
            self.close()
        try:
            if revents & EV_WRITE:
                self.on_writable()
            elif revents & EV_READ:
                self.on_readable()
        except _socket.error, e:
            if e.errno in NONBLOCKING:
                return
            self.close()
            logger.exception(e)
        except Exception, e:
            self.close()
            logger.exception(e)

    cdef on_readable(self):
        while self.is_readable():
            self.read()
        if self.is_ready():
            self.sink.ready(self.ready, self.buffer[LENGTH_SIZE:self.len])

    cdef on_writable(self):
        while self.is_writeable():
            self.write()
        if self.is_readable():
            self.wait_readable()
