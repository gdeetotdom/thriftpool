from setuptools import Extension, setup, find_packages
from Cython.Distutils import build_ext
import zmq


setup(
  name='thriftpool',
  cmdclass={'build_ext': build_ext},
  ext_modules=[Extension("socket_zmq.base",
                         ["socket_zmq/base.pyx"],
                         include_dirs=zmq.get_includes()),
               Extension("socket_zmq.source",
                         ["socket_zmq/source.pyx"],
                         include_dirs=zmq.get_includes()),
               Extension("socket_zmq.sink",
                         ["socket_zmq/sink.pyx"],
                         include_dirs=zmq.get_includes()),
               Extension("socket_zmq.pool",
                         ["socket_zmq/pool.pyx"],
                         include_dirs=zmq.get_includes()),
               Extension("socket_zmq.proxy",
                         ["socket_zmq/proxy.pyx"],
                         include_dirs=zmq.get_includes())],
  packages=find_packages(),
  install_requires=['pyzmq>=2.2.0,<3.0',
                    'Cython>=0.16',
                    'pyev'],
)
