import tempfile
import shutil
import os

from fabric.operations import local
from fabric.api import lcd

__all__ = ['generate_interfaces', 'generate_docs', 'upload_docs']


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


def upload_docs():
    """Upload generated documentation to github."""
    path = tempfile.mkdtemp()
    build = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         'docs', 'html')
    with lcd(path):
        local('git clone git@github.com:blackwithwhite666/thriftpool.git .')
        local('git checkout gh-pages')
        local('git rm -r .')
        local('touch .nojekyll')
        local('cp -r ' + build + '/* .')
        local('git stage .')
        local('git commit -a -m "Documentation updated."')
        local('git push origin gh-pages')
    shutil.rmtree(path)
