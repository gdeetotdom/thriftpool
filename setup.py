from setuptools import setup, find_packages, Extension
import os
import re
import sys

# Check requirements.

if sys.version_info < (2, 7):
    raise Exception('ThriftPool requires Python 2.7.')


# Which modules already present?

try:
    import Cython
    cython_installed = True
except ImportError:
    cython_installed = False

try:
    import zmq
    zmq_installed = True
except ImportError:
    zmq_installed = False


def extra_setup_args():
    result = {}
    if cython_installed:
        from Cython.Distutils import build_ext
        result['cmdclass'] = {'build_ext': build_ext}
    return result


# Description, version and other meta information.

re_meta = re.compile(r'__(\w+?)__\s*=\s*(.*)')
re_vers = re.compile(r'VERSION\s*=\s*\((.*?)\)')
re_doc = re.compile(r'^"""(.+?)"""')
rq = lambda s: s.strip("\"'")


def add_default(m):
    attr_name, attr_value = m.groups()
    return ((attr_name, rq(attr_value)),)


def add_version(m):
    v = list(map(rq, m.groups()[0].split(', ')))
    return (('VERSION', '.'.join(v[0:3]) + ''.join(v[3:])),)


def add_doc(m):
    return (('doc', m.groups()[0]),)

pats = {re_meta: add_default,
        re_vers: add_version,
        re_doc: add_doc}
here = os.path.abspath(os.path.dirname(__file__))
meta_fh = open(os.path.join(here, 'thriftpool/__init__.py'))
try:
    meta = {}
    for line in meta_fh:
        if line.strip() == '# -eof meta-':
            break
        for pattern, handler in pats.items():
            m = pattern.match(line.strip())
            if m:
                meta.update(handler(m))
finally:
    meta_fh.close()


# Describe existed entry points

entrypoints = {}
entrypoints['console_scripts'] = [
    'thriftpool = thriftpool.bin.orchestrator:main',
]


# Extensions definition

ext_modules = ["thriftpool.utils.exceptions"]


def get_ext_modules():
    if cython_installed:
        source_extension = ".pyx"
    else:
        source_extension = ".c"

    result = []
    for module in ext_modules:
        module_source = os.path.sep.join(module.split(".")) + source_extension
        result.append(Extension(
            module, sources=[module_source],
        ))
    return result


# External library definition

install_requires = ['thrift']


def get_extra_requires():
    if not zmq_installed:
        return ['pyzmq-static']
    return []


# Package data

package_data = {'thriftpool.utils': ['*.pyx']}


setup(name='thriftpool',
      version=meta['VERSION'],
      description=meta['doc'],
      author=meta['author'],
      author_email=meta['contact'],
      url=meta['homepage'],
      license='BSD',
      packages=find_packages(),
      package_data=package_data,
      install_requires=install_requires + get_extra_requires(),
      ext_modules=get_ext_modules(),
      entry_points=entrypoints,
      zip_safe=False,
      **extra_setup_args()
)
