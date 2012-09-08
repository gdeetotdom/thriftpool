from thriftpool.remote.ThriftPool import Client
from thrift import Thrift
from thrift.protocol import TBinaryProtocol
from thrift.transport import TSocket, TTransport
import sys
import time
if sys.platform == 'win32':
    _timer = time.clock
else:
    _timer = time.time


host = "127.0.0.1"
port = 51061

delta = 600


# Init thrift connection and protocol handlers
transport = TSocket.TSocket(host, port)
transport = TTransport.TFramedTransport(transport)
protocol = TBinaryProtocol.TBinaryProtocolAccelerated(transport)

# Set client to our Example
client = Client(protocol)

elapsed = 0
iterations = 1

while elapsed < delta:
    iterations *= 2

    t = _timer()
    transport.open()
    for i in xrange(iterations):
        #transport.open()
        client.ping()
        #transport.close()
    transport.close()
    elapsed = _timer() - t

print iterations, 'objects passed through connection in', elapsed, 'seconds'
print 'average number/sec:', iterations / elapsed
