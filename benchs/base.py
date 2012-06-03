import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from thrift_pool import balancer


frontend = "ipc://frontend"
backend = "ipc://backend"
factory = balancer.Factory(frontend, backend)
