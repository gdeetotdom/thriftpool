from Cython.Distutils import build_ext
from setuptools import setup, find_packages, Extension

setup(
  name='thriftpool',
  packages=find_packages(),
  install_requires=['pyzmq>=2.2.0,<3.0'],
  cmdclass={'build_ext': build_ext},
  ext_modules=[Extension("thriftpool.utils.exceptions",
                         ["thriftpool/utils/exceptions.pyx"])]
)
