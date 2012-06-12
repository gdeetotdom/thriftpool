from broker import *
from broker.ttypes import *
from thrift import Thrift
from thrift.protocol import TBinaryProtocol
from thrift.transport import TSocket, TTransport
import sys
import time
if sys.platform == 'win32':
    _timer = time.clock
else:
    _timer = time.time


host = "localhost"
port = 9090

delta = 10


# Init thrift connection and protocol handlers
transport = TSocket.TSocket(host, port)
transport = TTransport.TFramedTransport(transport)
protocol = TBinaryProtocol.TBinaryProtocol(transport)

# Set client to our Example
client = Broker.Client(protocol)

# Connect to server
transport.open()

task = Task('reverse', 'test word')

elapsed = 0
iterations = 1

while elapsed < delta:
    iterations *= 2

    t = _timer()
    for i in xrange(iterations):
        client.execute(task)
    elapsed = _timer() - t

print iterations, 'objects passed through connection in', elapsed, 'seconds'
print 'average number/sec:', iterations / elapsed


# Close connection
transport.close()

