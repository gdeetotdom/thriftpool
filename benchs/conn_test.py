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

delta = 5


# Init thrift connection and protocol handlers
transport = TSocket.TSocket(host, port)
transport = TTransport.TFramedTransport(transport)
protocol = TBinaryProtocol.TBinaryProtocol(transport)

# Set client to our Example
client = Broker.Client(protocol)

task = Task('reverse', 'test word')

elapsed = 0
iterations = 1

while elapsed < delta:
    iterations *= 2

    t = _timer()
    for i in xrange(iterations):
        try:
            transport.open()
            client.execute(task)
            transport.close()
        except Exception, e:
            raise
    elapsed = _timer() - t

print iterations, 'objects passed through connection in', elapsed, 'seconds'
print 'average number/sec:', iterations / elapsed
