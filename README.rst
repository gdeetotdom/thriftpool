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

.. |cistatus| image:: https://secure.travis-ci.org/gdeetotdom/thriftpool.png?branch=master
.. _`Thrift`: http://thrift.apache.org/
.. _`pyuv`: https://github.com/saghul/pyuv
.. _`libuv`: https://github.com/joyent/libuv
.. _`Cython`: http://www.cython.org/
.. _`Celery`: http://celeryproject.org/
