import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from socket_zmq import factory


backend = "ipc://backend"
factory = factory.Factory(backend)
