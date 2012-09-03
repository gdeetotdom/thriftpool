.. thriftpool documentation master file, created by
   sphinx-quickstart on Thu Aug  9 00:55:16 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

ThriftPool
==========

`ThriftPool` is an application server for `Thrift`_ services. It should create needed
sockets, start workers, serve requests from client and log them. It use `pyev`_ as
wrapper for `libev`_ and `ØMQ`_ for load balancing between workers. Request processing
written in `Cython`_.

.. note:: Currently it support only Thrift Framed protocol.

Key features:

* Fast request processing (~4000 rps);
* Compatibility with gevent through monkey patching;
* Support request logging;

.. _`Thrift`: http://thrift.apache.org/
.. _`pyev`: http://code.google.com/p/pyev/
.. _`libev`: http://software.schmorp.de/pkg/libev.html
.. _`ØMQ`: http://zeromq.github.com/pyzmq/
.. _`Cython`: http://www.cython.org/


Reference Docs
==============

.. toctree::
   :maxdepth: 1

   install
   basic_usage
   implementation
   api


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


License
=======

`ThriftPool` is open source and licensed under `BSD License`_.

.. _`BSD License`: http://www.opensource.org/licenses/BSD-3-Clause
