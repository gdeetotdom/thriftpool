from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext
import zmq

ext_modules = [Extension("gevent_thrift.connection",
                         ["gevent_thrift/connection.pyx"],
                         language="c++"),
               Extension("zeromq_pool.broker",
                         ["zeromq_pool/broker.pyx"],
                         language="c++", include_dirs=zmq.get_includes())]

setup(
  name='gevent_thrift',
  cmdclass={'build_ext': build_ext},
  ext_modules=ext_modules
)
