from setuptools import setup, find_packages


setup(
  name='thriftpool',
  packages=find_packages(),
  install_requires=['pyzmq>=2.2.0,<3.0'],
)
