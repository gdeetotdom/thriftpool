===========================================
ThriftPool - Container for thrift services.
===========================================

CI status: |cistatus|

`ThriftPool` is an application server for `Thrift`_ services. It should create needed
sockets, start workers, serve requests from client and log them. It use `pyev`_ as
wrapper for `libev`_ and `ØMQ`_ for load balancing between workers. Request processing
written in `Cython`_.

Key features:
- Fast request processing (~4000 rps);
- Compatibility with gevent through monkey patching;
- Support request logging.

.. |cistatus| image:: https://secure.travis-ci.org/blackwithwhite666/thriftpool.png?branch=master
.. _`Thrift`: http://thrift.apache.org/
.. _`pyev`: http://code.google.com/p/pyev/
.. _`libev`: http://software.schmorp.de/pkg/libev.html
.. _`ØMQ`: http://zeromq.github.com/pyzmq/
.. _`Cython`: http://www.cython.org/
