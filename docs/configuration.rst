Configuration Guide
===================

This guide explains how to configure the Plugin Adapter for different environments and cryptocurrency networks.

Environment Variables
---------------------

The Plugin Adapter uses environment variables for configuration. The primary configuration is:

UTXO_PLUGIN_LIST
   **Required**: Comma-separated list of cryptocurrency configurations.

   Format: ``CURRENCY1:HOST1,CURRENCY2:HOST2,...``

   Example:

   .. code-block:: bash

      export UTXO_PLUGIN_LIST='BLOCK:172.31.8.23,SYS:172.31.10.15,BTC:192.168.1.100'

   Each currency entry specifies:
   
   * ``CURRENCY``: The cryptocurrency symbol (e.g., BLOCK, BTC, LTC)
   * ``HOST``: The hostname or IP address of the ElectrumX server

Supported Currencies
--------------------

The Plugin Adapter supports the following cryptocurrencies:

* BLOCK - Blocknet
* BTC - Bitcoin
* BCH - Bitcoin Cash
* LTC - Litecoin
* DASH - Dash
* DOGE - Dogecoin
* DGB - DigiByte
* PIVX - PIVX
* RVN - Ravencoin
* SYS - Syscoin
* TZC - Terracoin
* XSN - StellarX
* UNO - Unobtanium
* PKOIN - PKOIN

Port Configuration
------------------

The Plugin Adapter connects to ElectrumX servers on port 9000 (port 8000 + 1000) by default.
Ensure that the specified hosts have ElectrumX servers running on the expected ports.

Configuration Examples
----------------------

Development Environment
   Single currency setup for testing:

   .. code-block:: bash

      export UTXO_PLUGIN_LIST='BLOCK:localhost'

Production Environment
   Multiple currencies with different servers:

   .. code-block:: bash

      export UTXO_PLUGIN_LIST='BLOCK:10.0.1.10,BTC:10.0.1.11,LTC:10.0.1.12,DASH:10.0.1.13'

High Availability
   Multiple servers for the same currency (load balancing):

   .. code-block:: bash

      export UTXO_PLUGIN_LIST='BLOCK:10.0.1.10,BLOCK:10.0.1.11,BTC:10.0.1.20'

Configuration Validation
------------------------

The service validates the configuration on startup:

1. **Currency validation**: Only supported currencies are accepted
2. **Host format validation**: Host must be a valid hostname or IP address
3. **Connection testing**: Attempts to connect to each ElectrumX server

Error messages during startup indicate configuration issues:

.. code-block:: text

   [config] Skipping unsupported currency: XYZ
   [config] Invalid UTXO_PLUGIN_LIST format for: BLOCK
   [adapter] Failed to connect to BLOCK: [Errno 111] Connection refused

Runtime Configuration
---------------------

Configuration is loaded once at startup. To apply configuration changes:

1. Stop the service
2. Update environment variables
3. Restart the service

Docker Configuration
--------------------

When using Docker, pass configuration via environment variables:

.. code-block:: bash

   docker run -d \
     --name plugin-adapter \
     -e UTXO_PLUGIN_LIST='BLOCK:172.31.8.23,SYS:172.31.10.15' \
     -p 5000:5000 \
     blocknetdx/plugin-adapter

For complex configurations, use environment file:

.. code-block:: bash

   echo "UTXO_PLUGIN_LIST=BLOCK:172.31.8.23,SYS:172.31.10.15" > .env

   docker run -d \
     --name plugin-adapter \
     --env-file .env \
     -p 5000:5000 \
     blocknetdx/plugin-adapter

Kubernetes Configuration
------------------------

Use ConfigMap or environment variables in your deployment:

.. code-block:: yaml

   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: plugin-adapter
   spec:
     template:
       spec:
         containers:
         - name: plugin-adapter
           image: blocknetdx/plugin-adapter
           env:
           - name: UTXO_PLUGIN_LIST
             value: "BLOCK:172.31.8.23,SYS:172.31.10.15"

Best Practices
--------------

1. **Use specific hostnames**: Avoid using localhost in production
2. **Monitor connections**: Check logs for connection issues
3. **Plan for redundancy**: Configure multiple servers for critical currencies
4. **Secure network access**: Ensure firewall rules allow connections to ElectrumX ports
5. **Test configuration**: Validate connections before deploying to production

Troubleshooting Configuration
-----------------------------

**Service fails to start**
   Check that UTXO_PLUGIN_LIST is set and contains valid currency symbols.

**Connection timeouts**
   Verify network connectivity to ElectrumX servers and correct host addresses.

**Invalid currency errors**
   Ensure all currencies in the list are supported (see Supported Currencies section).

**Mixed case issues**
   Currency symbols are case-sensitive and should be uppercase.

For additional help, see the :doc:`troubleshooting` guide or check the service logs.