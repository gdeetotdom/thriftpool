from contextlib import contextmanager

from thrift.transport import TSocket, TTransport
from thrift.protocol import TBinaryProtocol

from org.stubs.users import UserStorage


@contextmanager
def connect(host, port):
    """Create and open new transport to given host."""
    transport = TSocket.TSocket(host, port)
    transport = TTransport.TFramedTransport(transport)
    transport.open()
    try:
        yield transport
    finally:
        transport.close()


def main():
    with connect("localhost", 10005) as transport:
        # Talk to a server via TCP sockets, using a binary protocol
        protocol = TBinaryProtocol.TBinaryProtocol(transport)

        # Use the service we already defined
        service = UserStorage.Client(protocol)

        # Retrieve something as well
        print service.retrieve(2)


if __name__ == "__main__":
    main()
