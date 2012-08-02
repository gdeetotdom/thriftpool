from fabric.operations import local

__all__ = ['generate_interfaces']


def generate_interfaces():
    local('thrift --gen py:new_style,utf8strings,slots,dynamic -out ./ interfaces/thriftpool.thrift')
