Installation Guide
==================

This guide covers different methods to install and run the Plugin Adapter service.

Prerequisites
-------------

* Python 3.11 or later
* Docker (for containerized deployment)
* Network access to ElectrumX servers for supported cryptocurrencies

Docker Installation (Recommended)
---------------------------------

The easiest way to install and run the Plugin Adapter is using Docker.

Pull the Docker image:

.. code-block:: bash

   docker pull blocknetdx/plugin-adapter:latest

Run the container:

.. code-block:: bash

   docker run -d \
     --name plugin-adapter \
     -e UTXO_PLUGIN_LIST='BLOCK:172.31.8.23,SYS:172.31.10.15' \
     -p 5000:5000 \
     blocknetdx/plugin-adapter

Verify the service is running:

.. code-block:: bash

   docker logs plugin-adapter

Manual Installation
-------------------

Clone the repository:

.. code-block:: bash

   git clone https://github.com/your-org/plugin-adapter.git
   cd plugin-adapter

Install Python dependencies:

.. code-block:: bash

   pip install -r requirements.txt

Set up environment variables:

.. code-block:: bash

   export UTXO_PLUGIN_LIST='BLOCK:172.31.8.23,SYS:172.31.10.15'

Run the service:

.. code-block:: bash

   python plugin-adapter.py

Verification
------------

Test the installation by making a simple request:

.. code-block:: bash

   curl -X POST http://localhost:5000/ \
     -H "Content-Type: application/json" \
     -d '{"method": "ping", "params": []}'

You should receive a response like:

.. code-block:: json

   {"result": 1, "error": null}

Troubleshooting Installation Issues
-----------------------------------

**Port already in use**
   If port 5000 is already in use, you can specify a different port:

   .. code-block:: bash

      docker run -d \
        --name plugin-adapter \
        -e UTXO_PLUGIN_LIST='BLOCK:172.31.8.23,SYS:172.31.10.15' \
        -p 8080:5000 \
        blocknetdx/plugin-adapter

**Network connectivity issues**
   Ensure your system can reach the ElectrumX servers specified in UTXO_PLUGIN_LIST.
   You can test connectivity with:

   .. code-block:: bash

      telnet <electrumx_host> 9000

**Missing environment variable**
   The service requires the UTXO_PLUGIN_LIST environment variable to be set.
   See the :doc:`configuration` guide for details.

Next Steps
----------

After installation, proceed to the :doc:`configuration` guide to set up your cryptocurrency connections, or explore the :doc:`api-reference` to learn about available endpoints.