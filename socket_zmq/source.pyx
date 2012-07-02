cimport cython
from libc.stdlib cimport realloc, free

from socket_zmq.pool cimport SinkPool
from socket_zmq.base cimport BaseSocket
from socket_zmq.sink cimport ZMQSink

from pyev import EV_READ, EV_WRITE, EV_ERROR
from struct import Struct, calcsize, pack_into
import _socket
import errno
from zmq.utils.buffers cimport frombuffer_2, PyBuffer_FromReadWriteObject

from logging import getLogger

logger = getLogger(__name__)

NONBLOCKING = (errno.EAGAIN, errno.EWOULDBLOCK)
LENGTH_FORMAT = '!i'
cdef int LENGTH_SIZE = calcsize(LENGTH_FORMAT)
cdef int BUFFER_SIZE = 4096


cdef class Buffer:

    def __cinit__(self):
        self.length = 0
        self.handle = NULL

    def __init__(self):
        self.view = None

    def __dealloc__(self):
        if self.handle != NULL:
            free(self.handle)

    cdef resize(self, int size):
        if self.length < size:
            self.length = size
            self.handle = realloc(self.handle, self.length * sizeof(unsigned char))
            self.view = frombuffer_2(self.handle, self.length, 0)

    cdef slice(self, int offset, int size=0):
        cdef int nbytes = size or self.length - offset
        return PyBuffer_FromReadWriteObject(self.view, offset, nbytes)


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
                 object address, object on_close):

        self.sent_bytes = self.recv_bytes = self.len = 0
        self.status = WAIT_LEN

        self.struct = Struct(LENGTH_FORMAT)

        self.buffer = Buffer()
        self.buffer.resize(BUFFER_SIZE)

        self.address = address
        self.on_close = on_close
        self.socket = socket
        self.pool = pool
        self.sink = self.pool.get()

        BaseSocket.__init__(self, loop, self.socket.fileno())

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
        received = self.socket.recv_into(self.buffer.view, self.buffer.length)

        if received == 0:
            # if we read 0 bytes and message is empty, it means client
            # close connection
            self.close()
            return 0

        assert received >= LENGTH_SIZE, "message length can't be read"

        message_length = self.struct.unpack_from(self.buffer.slice(0))[0]

        assert message_length > 0, "negative or empty frame size, it seems" \
                                   " client doesn't use FramedTransport"

        self.len = message_length + LENGTH_SIZE

        self.buffer.resize(self.len)

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
            readed = self.socket.recv_into(self.buffer.slice(self.recv_bytes),
                                           self.len - self.recv_bytes)

        assert readed > 0, "can't read frame from socket"

        self.recv_bytes += readed
        if self.recv_bytes == self.len:
            self.recv_bytes = 0
            self.status = WAIT_PROCESS

    cdef inline write(self):
        """Writes data from socket and switch state."""
        assert self.is_writeable(), 'socket in non writable state'

        self.sent_bytes += self.socket.send(self.buffer.slice(self.sent_bytes,
                                                self.len - self.sent_bytes))

        if self.sent_bytes == self.len:
            self.status = WAIT_LEN
            self.len = 0
            self.sent_bytes = 0

    cpdef close(self):
        """Closes connection."""
        assert not self.is_closed(), 'socket already closed'

        # close socket
        self.status = CLOSED
        self.socket.close()

        # close sink if needed
        if self.sink.is_ready():
            # sink is ready, return to pool
            self.pool.put(self.sink)
        elif not self.sink.is_closed():
            # sink is not closed, close it
            self.sink.close()
        self.pool = self.sink = None

        # execute callback
        self.on_close(self)
        self.on_close = None

        # remove objects
        self.buffer = None

        BaseSocket.close(self)

    @cython.locals(message_length=cython.int)
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
        self.len = message_length + LENGTH_SIZE

        if message_length == 0:
            # it was a oneway request, do not write answer
            self.status = WAIT_LEN
        else:
            # resize buffer if needed
            self.buffer.resize(self.len)
            # pack message size
            self.struct.pack_into(self.buffer.slice(0), 0, message_length)
            # copy message to buffer
            self.buffer.view[LENGTH_SIZE:self.len] = message
            self.status = SEND_ANSWER
            self.wait_writable()

    cpdef cb_io(self, object watcher, object revents):
        try:
            if revents & EV_WRITE:
                self.on_writable()
            elif revents & EV_READ:
                self.on_readable()

        except _socket.error, exc:
            if exc.errno in NONBLOCKING:
                # socket can't be processed now, return
                return
            logger.error(exc, exc_info=1, extra={'host': self.address[0],
                                                 'port': self.address[1]})
            self.close()

        except Exception, exc:
            logger.error(exc, exc_info=1, extra={'host': self.address[0],
                                                 'port': self.address[1]})
            self.close()

    cdef on_readable(self):
        while self.is_readable():
            self.read()
        if self.is_ready():
            self.sink.ready(self.ready, self.buffer.slice(LENGTH_SIZE,
                                                    self.len - LENGTH_SIZE))

    cdef on_writable(self):
        while self.is_writeable():
            self.write()
        if self.is_readable():
            self.wait_readable()
