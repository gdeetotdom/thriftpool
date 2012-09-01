from fabric.operations import local
from fabric.api import lcd

__all__ = ['generate_interfaces', 'generate_docs']


def generate_interfaces():
    local('thrift --gen py:new_style,utf8strings,slots,dynamic -out ./ interfaces/thriftpool.thrift')


def generate_docs(clean='no'):
    """Generate the Sphinx documentation."""
    c = ""
    local('sphinx-apidoc -f -o docs/source/api thriftpool')
    if clean.lower() in ['yes', 'y']:
        c = "clean "
    with lcd('docs'):
        local('make %shtml' % c)
