from setuptools import Extension, setup, find_packages
from Cython.Distutils import build_ext


def get_ext_modules():
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
    return ext_modules


setup(
  name='thriftpool',
  cmdclass={'build_ext': build_ext},
  ext_modules=get_ext_modules(),
  packages=find_packages(),
)
