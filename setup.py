import os
import re
import sys

from setuptools import setup, find_packages

# Check requirements.

if sys.version_info < (2, 7):
    raise Exception('ThriftPool requires Python 2.7.')


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

with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()

with open(os.path.join(here, 'CHANGES.rst')) as f:
    CHANGES = f.read()


# Describe existed entry points

entrypoints = {}
entrypoints['console_scripts'] = [
    'thriftpoold = thriftpool.bin.thriftpoold:main',
    'thriftpool = thriftpool.bin.thriftpoolctl:main',
]
entrypoints['thriftpool.modules'] = []


setup(name='thriftpool',
      version=meta['VERSION'],
      description=meta['doc'],
      author=meta['author'],
      author_email=meta['contact'],
      url=meta['homepage'],
      long_description=README + '\n\n' + CHANGES,
      keywords='thrift soa',
      license='BSD',
      packages=find_packages(),
      install_requires=['thrift', 'pyuv>=0.8.3', 'six',
                        'gaffer>=0.4.4', 'thriftworker>=0.1.16'],
      entry_points=entrypoints,
      zip_safe=False
)
