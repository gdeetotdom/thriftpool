from thrift_pool import balancer


frontend = "ipc://frontend"
backend = "ipc://backend"
factory = balancer.Factory(frontend, backend)
