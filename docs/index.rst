Plugin Adapter Documentation
============================

A high-performance cryptocurrency adapter service providing unified RPC interface for multiple cryptocurrencies.

.. toctree::
   :maxdepth: 3
   :caption: Contents:

   installation
   configuration
   api-reference
   deployment
   architecture
   troubleshooting

Overview
--------

The Plugin Adapter is a modular service that bridges applications with multiple cryptocurrency networks through the ElectrumX protocol. It provides a unified RPC interface supporting 14+ cryptocurrencies with thread-safe architecture and comprehensive error handling.

Key Features
------------

* **Multi-currency support**: 14+ supported cryptocurrencies (BLOCK, BTC, BCH, LTC, DASH, DOGE, DGB, PIVX, RVN, SYS, TZC, XSN, UNO, PKOIN)
* **Thread-safe architecture**: Proper async patterns with thread-safe configuration management
* **High performance**: Concurrent request processing with connection pooling
* **Comprehensive error handling**: Standardized error responses and exception handling
* **Built-in monitoring**: Heartbeat monitoring and health checks
* **Container ready**: Docker and Kubernetes deployment support

Quick Links
-----------

* :ref:`genindex`
* :ref:`search`
* `GitHub Repository <https://github.com/your-org/plugin-adapter>`_
* `Issue Tracker <https://github.com/your-org/plugin-adapter/issues>`_

Getting Started
---------------

For new users, we recommend starting with the :doc:`installation` guide, followed by :doc:`configuration` to set up your environment. Then explore the :doc:`api-reference` to understand the available endpoints and methods.
