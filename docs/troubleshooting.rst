Troubleshooting Guide
====================

This guide helps you diagnose and resolve common issues with the Plugin Adapter service.

Service Startup Issues
----------------------

Service Won't Start
~~~~~~~~~~~~~~~~~~~~

**Error**: "UTXO_PLUGIN_LIST environment variable not set"

.. code-block:: text

   [adapter] FATAL: UTXO_PLUGIN_LIST environment variable not set

**Solution**: Set the required environment variable:

.. code-block:: bash

   export UTXO_PLUGIN_LIST='BLOCK:172.31.8.23,SYS:172.31.10.15'

**Error**: "Invalid UTXO_PLUGIN_LIST format"

.. code-block:: text

   [config] Invalid UTXO_PLUGIN_LIST format for: BLOCK

**Solution**: Ensure correct format ``CURRENCY:HOST,CURRENCY:HOST``:

.. code-block:: bash

   # Correct format
   export UTXO_PLUGIN_LIST='BLOCK:172.31.8.23,SYS:172.31.10.15'
   
   # Incorrect - missing host
   export UTXO_PLUGIN_LIST='BLOCK,SYS'

**Error**: "Unsupported currency"

.. code-block:: text

   [config] Skipping unsupported currency: XYZ

**Solution**: Use only supported currencies: BLOCK, BTC, BCH, LTC, DASH, DOGE, DGB, PIVX, RVN, SYS, TZC, XSN, UNO, PKOIN

Port Already in Use
~~~~~~~~~~~~~~~~~~~~

**Error**: "Address already in use"

.. code-block:: text

   OSError: [Errno 98] Address already in use

**Solution**: Use a different port:

.. code-block:: bash

   # Docker
   docker run -d -p 8080:5000 ...
   
   # Manual
   # Modify the port in plugin-adapter.py main() function

Connection Issues
-----------------

Cannot Connect to ElectrumX Servers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Error**: "Failed to connect to [currency]"

.. code-block:: text

   [adapter] Failed to connect to BLOCK: [Errno 111] Connection refused

**Diagnosis**: Test network connectivity:

.. code-block:: bash

   # Test with telnet
   telnet 172.31.8.23 9000
   
   # Test with netcat
   nc -zv 172.31.8.23 9000

**Solutions**:

1. **Check host address**: Verify the ElectrumX server IP/hostname
2. **Check port**: Ensure ElectrumX is running on port 9000 (8000 + 1000)
3. **Check firewall**: Ensure network access to the ElectrumX server
4. **Check ElectrumX status**: Verify the ElectrumX service is running

Timeout Errors
~~~~~~~~~~~~~~~

**Error**: "Timeout during request"

.. code-block:: text

   [server] ERROR: Error during getblockcount grabbing! asyncio.TimeoutError

**Solutions**:

1. **Check ElectrumX performance**: Server might be overloaded
2. **Network latency**: High latency between services
3. **Increase timeout**: Modify timeout values in the code (not recommended)
4. **Scale ElectrumX**: Add more ElectrumX instances

API Issues
----------

No Response from API
~~~~~~~~~~~~~~~~~~~~~

**Issue**: API requests hang or timeout

**Diagnosis**:

.. code-block:: bash

   # Test basic connectivity
   curl -I http://localhost:5000/
   
   # Test with verbose output
   curl -v http://localhost:5000/ \
     -H "Content-Type: application/json" \
     -d '{"method": "ping", "params": []}'

**Solutions**:

1. **Check service status**: Ensure the service is running
2. **Check port binding**: Verify the service is listening on the expected port
3. **Check firewall**: Ensure port access is not blocked
4. **Check logs**: Look for error messages in service logs

Invalid JSON Response
~~~~~~~~~~~~~~~~~~~~~

**Error**: "Expecting value: line 1 column 1 (char 0)"

**Cause**: Service returned empty response or error

**Solutions**:

1. **Check service logs**: Look for internal errors
2. **Check request format**: Ensure valid JSON in request body
3. **Check content-type**: Set ``Content-Type: application/json``

Method Not Found
~~~~~~~~~~~~~~~~

**Error**: "Method not found" or similar

**Cause**: Invalid RPC method name

**Solutions**:

1. **Check method name**: Use supported methods (getutxos, getrawtransaction, etc.)
2. **Check case sensitivity**: Method names are case-sensitive
3. **Check API documentation**: Refer to :doc:`api-reference`

Currency-Specific Errors
------------------------

Unsupported Currency
~~~~~~~~~~~~~~~~~~~~~

**Error**: "Attempted to get UTXOs from unsupported coin XYZ"

**Solution**: Ensure the currency is in your UTXO_PLUGIN_LIST configuration:

.. code-block:: bash

   echo $UTXO_PLUGIN_LIST

Invalid Address Format
~~~~~~~~~~~~~~~~~~~~~~

**Error**: "ValidationError" or parsing errors

**Solutions**:

1. **Check address format**: Ensure address is valid for the currency
2. **Check address case**: Some currencies require specific case
3. **Test with known good address**: Use a test address first

Transaction Errors
~~~~~~~~~~~~~~~~~~

**Error**: "Transaction rejected" or "-25" error code

**Causes**:

1. **Invalid transaction**: Malformed transaction data
2. **Insufficient funds**: Not enough balance
3. **Invalid signature**: Transaction not properly signed
4. **Network issues**: ElectrumX server problems

**Solutions**:

1. **Validate transaction**: Check transaction format and signatures
2. **Check balance**: Ensure sufficient funds
3. **Retry with different ElectrumX**: Try alternative server

Performance Issues
------------------

High Response Times
~~~~~~~~~~~~~~~~~~~

**Symptoms**: Slow API responses

**Diagnosis**:

.. code-block:: bash

   # Measure response time
   time curl -X POST http://localhost:5000/ \
     -H "Content-Type: application/json" \
     -d '{"method": "getblockcount", "params": ["BLOCK"]}'

**Solutions**:

1. **Check ElectrumX performance**: Monitor ElectrumX server load
2. **Check network latency**: Measure network delays
3. **Scale horizontally**: Add more Plugin Adapter instances
4. **Optimize configuration**: Review timeout and connection settings

High Memory Usage
~~~~~~~~~~~~~~~~~

**Symptoms**: Service using excessive memory

**Diagnosis**:

.. code-block:: bash

   # Check memory usage
   docker stats
   # or
   ps aux | grep plugin-adapter

**Solutions**:

1. **Monitor connections**: Check number of active connections
2. **Restart service**: Clear any memory leaks
3. **Scale horizontally**: Distribute load across multiple instances

High CPU Usage
~~~~~~~~~~~~~~

**Symptoms**: High CPU utilization

**Causes**:

1. **High request volume**: Too many concurrent requests
2. **Network timeouts**: Waiting for slow ElectrumX responses
3. **Infinite loops**: Software bugs

**Solutions**:

1. **Monitor request rate**: Implement rate limiting
2. **Check ElectrumX health**: Ensure backend servers are healthy
3. **Scale horizontally**: Add more instances

Monitoring and Logs
-------------------

Accessing Logs
~~~~~~~~~~~~~~

**Docker**:

.. code-block:: bash

   docker logs plugin-adapter
   docker logs -f plugin-adapter  # Follow logs

**Kubernetes**:

.. code-block:: bash

   kubectl logs deployment/plugin-adapter -n crypto-services
   kubectl logs -f deployment/plugin-adapter -n crypto-services

**File logs**:

.. code-block:: bash

   tail -f debug.log

Log Analysis
~~~~~~~~~~~~

**Key log messages to watch for**:

.. code-block:: text

   [adapter] Plugin adapter started successfully  # Normal startup
   [config] Loaded configuration for BLOCK: 172.31.8.23:8000  # Normal config
   [heartbeat] BLOCK: Height (DB/Daemon): 123456 / 123456 blocks  # Normal heartbeat
   [adapter] Failed to connect to BLOCK: [Errno 111] Connection refused  # Connection issue
   [server] Execution time for 'get_block_count' BLOCK: 5.234 seconds  # Slow response

Debug Mode
~~~~~~~~~~

Enable debug logging:

.. code-block:: bash

   # Set log level to DEBUG
   # Modify logging configuration in plugin-adapter.py

Health Checks
~~~~~~~~~~~~~

**Basic connectivity**:

.. code-block:: bash

   curl -X POST http://localhost:5000/ \
     -H "Content-Type: application/json" \
     -d '{"method": "ping", "params": []}'

**Service and backend health**:

.. code-block:: bash

   curl http://localhost:5000/height
   curl http://localhost:5000/fees

**Expected responses**:

.. code-block:: json

   {"result": 1, "error": null}  # ping
   {"result": {"BLOCK": 123456}, "error": null}  # height
   {"result": {"BLOCK": 0.00012345}, "error": null}  # fees

Common Error Patterns
---------------------

Network Errors (Code -1)
~~~~~~~~~~~~~~~~~~~~~~~~

**Causes**:

* ElectrumX server down
* Network connectivity issues
* Firewall blocking connections

**Solutions**:

1. Check ElectrumX server status
2. Verify network connectivity
3. Check firewall rules

Protocol Errors (Code -2)
~~~~~~~~~~~~~~~~~~~~~~~~~

**Causes**:

* ElectrumX protocol errors
* Server-side issues
* Invalid requests

**Solutions**:

1. Check ElectrumX logs
2. Verify request format
3. Retry with different parameters

Validation Errors (Code -5)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Causes**:

* Invalid addresses
* Malformed transaction data
* Invalid parameters

**Solutions**:

1. Validate input data
2. Check address formats
3. Verify transaction structure

Getting Help
------------

When to Seek Help
~~~~~~~~~~~~~~~~~

* Issues not covered in this guide
* Persistent connection problems
* Performance issues that don't resolve
* Security concerns

Information to Include
~~~~~~~~~~~~~~~~~~~~~~

When reporting issues, include:

1. **Service version**: Output of service startup
2. **Configuration**: UTXO_PLUGIN_LIST (with sensitive info redacted)
3. **Error logs**: Relevant log entries
4. **Steps to reproduce**: How to trigger the issue
5. **Environment details**: Docker/Kubernetes version, OS, etc.

Useful Commands
~~~~~~~~~~~~~~~

.. code-block:: bash

   # Check service status
   docker ps | grep plugin-adapter
   
   # Check service logs
   docker logs --tail=50 plugin-adapter
   
   # Test connectivity
   curl -s http://localhost:5000/height
   
   # Check network connectivity
   telnet <electrumx_host> 9000
   
   # Monitor resource usage
   docker stats plugin-adapter

For additional guidance, refer to the :doc:`installation`, :doc:`configuration`, and :doc:`deployment` guides.