API Reference
=============

The Plugin Adapter provides a unified RPC interface for interacting with multiple cryptocurrency networks.

Base URL
--------

All requests are made to the service's base URL:

``http://localhost:5000``

Replace ``localhost`` with your service hostname as needed.

Authentication
--------------

The API does not require authentication. Ensure proper network security when deploying.

Request Format
--------------

All RPC requests use POST method with JSON content:

.. code-block:: http

   POST / HTTP/1.1
   Content-Type: application/json

   {
     "method": "getutxos",
     "params": ["BLOCK", "your_address"]
   }

Response Format
---------------

Successful responses:

.. code-block:: json

   {
     "result": {...},
     "error": null
   }

Error responses:

.. code-block:: json

   {
     "result": null,
     "error": {
       "code": -1,
       "message": "Error description",
       "type": "NetworkError"
     }
   }

Error Codes
-----------

.. list-table::
   :widths: 10 30 60
   :header-rows: 1

   * - Code
     - Type
     - Description
   * - -1
     - NetworkError
     - Network connectivity issues
   * - -2
     - ProtocolError
     - Protocol or server errors
   * - -5
     - ValidationError
     - Invalid request parameters
   * - -10
     - ConfigurationError
     - Configuration issues
   * - -25
     - TransactionError
     - Transaction processing errors

RPC Methods
-----------

getutxos
~~~~~~~~~

Get unspent transaction outputs for an address.

**Parameters:**

.. list-table::
   :widths: 20 30 50
   :header-rows: 1

   * - Position
     - Type
     - Description
   * - 0
     - string
     - Currency symbol (e.g., "BLOCK", "BTC")
   * - 1
     - string or array
     - Address(es) to query (JSON string or array)

**Example:**

.. code-block:: bash

   curl -X POST http://localhost:5000/ \
     -H "Content-Type: application/json" \
     -d '{"method": "getutxos", "params": ["BLOCK", "BwEgtC9p5nEY2qQ7tQ2T8wKXtG9Q2T8wKX"]}'

**Response:**

.. code-block:: json

   {
     "result": {
       "utxos": [
         {
           "address": "BwEgtC9p5nEY2qQ7tQ2T8wKXtG9Q2T8wKX",
           "txhash": "a1b2c3d4e5f6...",
           "vout": 0,
           "block_number": 123456,
           "value": 0.5
         }
       ]
     },
     "error": null
   }

getrawtransaction
~~~~~~~~~~~~~~~~~

Get raw transaction data.

**Parameters:**

.. list-table::
   :widths: 20 30 50
   :header-rows: 1

   * - Position
     - Type
     - Description
   * - 0
     - string
     - Currency symbol
   * - 1
     - string
     - Transaction ID
   * - 2
     - boolean (optional)
     - Verbose output (default: false)

**Example:**

.. code-block:: bash

   curl -X POST http://localhost:5000/ \
     -H "Content-Type: application/json" \
     -d '{"method": "getrawtransaction", "params": ["BLOCK", "a1b2c3d4e5f6...", true]}'

getblockcount
~~~~~~~~~~~~~

Get current block count.

**Parameters:**

.. list-table::
   :widths: 20 30 50
   :header-rows: 1

   * - Position
     - Type
     - Description
   * - 0
     - string
     - Currency symbol

**Example:**

.. code-block:: bash

   curl -X POST http://localhost:5000/ \
     -H "Content-Type: application/json" \
     -d '{"method": "getblockcount", "params": ["BLOCK"]}'

**Response:**

.. code-block:: json

   {
     "result": 123456,
     "error": null
   }

getbalance
~~~~~~~~~~

Get address balance.

**Parameters:**

.. list-table::
   :widths: 20 30 50
   :header-rows: 1

   * - Position
     - Type
     - Description
   * - 0
     - string
     - Currency symbol
   * - 1
     - string
     - Address to check

**Response:**

.. code-block:: json

   {
     "result": {
       "confirmed": 1.5,
       "unconfirmed": 0.0
     },
     "error": null
   }

sendrawtransaction
~~~~~~~~~~~~~~~~~~

Broadcast a raw transaction.

**Parameters:**

.. list-table::
   :widths: 20 30 50
   :header-rows: 1

   * - Position
     - Type
     - Description
   * - 0
     - string
     - Currency symbol
   * - 1
     - string
     - Raw transaction hex

**Response:**

.. code-block:: json

   {
     "result": "txid_hash_here",
     "error": null
   }

Monitoring Endpoints
--------------------

These endpoints provide service status and aggregate data.

/height
~~~~~~~

Get block heights for all configured currencies.

**Request:**

.. code-block:: http

   GET /height HTTP/1.1

**Response:**

.. code-block:: json

   {
     "result": {
       "BLOCK": 123456,
       "BTC": 789012,
       "LTC": 345678
     },
     "error": null
   }

/fees
~~~~~

Get transaction fees for all configured currencies.

**Request:**

.. code-block:: http

   GET /fees HTTP/1.1

**Response:**

.. code-block:: json

   {
     "result": {
       "BLOCK": 0.00012345,
       "BTC": 0.00056789,
       "LTC": 0.00001234
     },
     "error": null
   }

/ping
~~~~~

Health check endpoint.

**Request:**

.. code-block:: http

   POST / HTTP/1.1
   Content-Type: application/json

   {"method": "ping", "params": []}

**Response:**

.. code-block:: json

   {
     "result": 1,
     "error": null
   }

Rate Limiting
-------------

The service does not implement built-in rate limiting. Implement rate limiting at the proxy or load balancer level if needed.

Timeouts
--------

* Connection timeout: 15 seconds
* Request timeout: 30 seconds (60 seconds for batch requests)
* Heartbeat interval: 2 seconds

Best Practices
--------------

1. **Handle errors gracefully**: Always check the ``error`` field in responses
2. **Use appropriate timeouts**: Set client-side timeouts longer than server timeouts
3. **Monitor connection health**: Use the ``/ping`` endpoint for health checks
4. **Batch requests when possible**: Use array parameters for multiple addresses
5. **Validate addresses**: Ensure addresses are valid for the target currency
6. **Handle network errors**: Implement retry logic for network-related errors

For deployment and configuration guidance, see the :doc:`deployment` and :doc:`configuration` guides.