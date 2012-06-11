from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext
import zmq


ext_modules = [Extension("socket_zmq.source",
                         ["socket_zmq/source.pyx"],
                         include_dirs=zmq.get_includes()),
               Extension("socket_zmq.sink",
                         ["socket_zmq/sink.pyx"],
                         include_dirs=zmq.get_includes()),
               Extension("socket_zmq.connection",
                         ["socket_zmq/connection.pyx"],
                         include_dirs=zmq.get_includes()),
               Extension("socket_zmq.server",
                         ["socket_zmq/server.pyx"],
                         include_dirs=zmq.get_includes())]


setup(
  name='socket_zmq',
  cmdclass={'build_ext': build_ext},
  ext_modules=ext_modules
)
