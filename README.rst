===========================================
ThriftPool - Container for thrift services.
===========================================

CI status: |cistatus|

`ThriftPool` is an application server for `Thrift`_ services. It should create needed
sockets, start workers, serve requests from client and log them. It use `pyuv`_ as
wrapper for `libuv`_ and pre-fork model for load balancing between workers. Request processing
written in `Cython`_.

Key features:

* Pre-fork worker model;
* Fast request processing (~3500 rps);
* Compatibility with gevent through monkey patching;
* Support request logging.

Code of project based on `Celery`_.

.. |cistatus| image:: https://secure.travis-ci.org/blackwithwhite666/thriftpool.png?branch=master
.. _`Thrift`: http://thrift.apache.org/
.. _`pyuv`: http://code.google.com/p/pyev/
.. _`libuv`: http://software.schmorp.de/pkg/libev.html
.. _`ØMQ`: http://zeromq.github.com/pyzmq/
.. _`Cython`: http://www.cython.org/
.. _`Celery`: http://celeryproject.org/
