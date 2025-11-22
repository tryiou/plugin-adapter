Architecture Documentation
==========================

This document describes the architecture and design principles of the Plugin Adapter service.

Overview
--------

The Plugin Adapter is a modular, thread-safe service that provides a unified RPC interface for multiple cryptocurrency networks. It uses the ElectrumX protocol to communicate with various cryptocurrency backends and presents a consistent API to client applications.

Architecture Principles
-----------------------

**Modular Design**
   Components are organized into clearly separated modules with well-defined responsibilities.

**Thread Safety**
   All components are designed to be thread-safe, eliminating race conditions and data corruption.

**Async Performance**
   Uses asyncio and async/await patterns for optimal concurrent request handling.

**Error Resilience**
   Comprehensive error handling with graceful degradation and standardized error responses.

**Configuration Flexibility**
   Environment-based configuration that can be easily adapted to different deployment scenarios.

Component Architecture
----------------------

High-Level Architecture
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   Client Applications
           ↓ (HTTP/JSON-RPC)
   ┌─────────────────────────┐
   │    Application Server   │
   │   (aiohttp + Router)    │
   └─────────────────────────┘
           ↓ (Dispatch)
   ┌─────────────────────────┐
   │     RPC Handlers        │
   │  (UTXO, TX, Block, etc) │
   └─────────────────────────┘
           ↓ (Configuration)
   ┌─────────────────────────┐
   │   Configuration Manager │
   │   (Thread-safe config)  │
   └─────────────────────────┘
           ↓ (TCP/async)
   ┌─────────────────────────┐
   │    Networking Layer     │
   │   (ElectrumX Protocol)  │
   └─────────────────────────┘
           ↓ (RPC)
   ┌─────────────────────────┐
   │   ElectrumX Servers     │
   │  (BLOCK, BTC, LTC, etc) │
   └─────────────────────────┘

Core Components
---------------

Application Server
~~~~~~~~~~~~~~~~~~

**Location**: ``src/core/application.py``

The Application Server is the main entry point that manages the HTTP server and application lifecycle.

Key responsibilities:

* HTTP server management using aiohttp
* Route registration and request routing
* Application startup and shutdown
* Signal handling for graceful shutdown
* Heartbeat management coordination

**Classes**:

* ``PluginAdapterApplication`` - Main application orchestrator
* ``ApplicationServer`` - HTTP server management
* ``HeartbeatManager`` - Connection monitoring

RPC Handlers
~~~~~~~~~~~~

**Location**: ``src/services/rpc_handlers.py``

RPC Handlers process incoming JSON-RPC requests and delegate to appropriate cryptocurrency backends.

Handler types:

* ``UTXORPCHandler`` - UTXO-related operations
* ``TransactionRPCHandler`` - Transaction operations  
* ``BlockRPCHandler`` - Block operations
* ``BalanceRPCHandler`` - Balance queries
* ``HistoryRPCHandler`` - Transaction history
* ``UtilityRPCHandler`` - Utility methods

Each handler:

* Validates currency support
* Retrieves appropriate socket connection
* Formats requests and responses
* Handles errors and timeouts

Configuration Manager
~~~~~~~~~~~~~~~~~~~~~

**Location**: ``src/core/configuration.py``

The Configuration Manager provides thread-safe access to cryptocurrency configurations and manages socket connections.

Key features:

* Thread-safe configuration storage using locks
* Currency validation and filtering
* Socket connection management
* Environment variable parsing
* Runtime configuration access

**Classes**:

* ``ConfigurationManager`` - Main configuration manager
* ``CoinConfig`` - Individual currency configuration

Networking Layer
~~~~~~~~~~~~~~~~

**Location**: ``src/networking/tcp_socket.py``

The Networking Layer handles TCP connections to ElectrumX servers and RPC message transmission.

Key responsibilities:

* TCP connection establishment and management
* Async message sending and receiving
* Connection pooling and reuse
* Timeout handling
* Error detection and recovery

**Classes**:

* ``TCPSocket`` - TCP connection wrapper for ElectrumX communication

Error Handling
~~~~~~~~~~~~~~

**Location**: ``src/core/error_handling.py``

Comprehensive error handling system with standardized error responses.

Error types:

* ``NetworkError`` - Network connectivity issues (-1)
* ``ProtocolError`` - Protocol or server errors (-2)
* ``TransactionError`` - Transaction processing errors (-25)
* ``ValidationError`` - Invalid request parameters (-5)
* ``ConfigurationError`` - Configuration issues (-10)

Data Flow
---------

Request Processing Flow
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   1. HTTP Request Received
      ↓
   2. Route Matching (POST /)
      ↓
   3. JSON-RPC Parsing
      ↓
   4. Method Dispatch
      ↓
   5. Handler Selection
      ↓
   6. Currency Validation
      ↓
   7. Socket Connection Retrieval
      ↓
   8. ElectrumX Request
      ↓
   9. Response Processing
      ↓
   10. Error Handling
      ↓
   11. JSON Response

Concurrent Processing
~~~~~~~~~~~~~~~~~~~~~

The service handles multiple requests concurrently:

1. **HTTP Level**: aiohttp handles multiple HTTP connections
2. **Application Level**: Async request processing
3. **Network Level**: Concurrent ElectrumX requests using asyncio.gather()
4. **Heartbeat**: Background connection monitoring

Configuration Flow
~~~~~~~~~~~~~~~~~~

.. code-block:: text

   1. Environment Variable (UTXO_PLUGIN_LIST)
      ↓
   2. Configuration Manager Load
      ↓
   3. Currency Parsing and Validation
      ↓
   4. Socket Connection Setup
      ↓
   5. Heartbeat Initialization
      ↓
   6. Runtime Configuration Access

Threading Model
---------------

Main Thread
~~~~~~~~~~~~

* HTTP server event loop
* Request handling and routing
* Configuration management
* Signal handling

Background Threads
~~~~~~~~~~~~~~~~~~

* Heartbeat monitoring thread
* Async task execution within event loop

Thread Safety Measures
~~~~~~~~~~~~~~~~~~~~~~

* ``ConfigurationManager`` uses thread locks
* Async operations use asyncio.Lock
* No shared mutable state between threads
* Proper async patterns avoid thread creation in async context

Performance Characteristics
---------------------------

Concurrency
~~~~~~~~~~~

* **HTTP Concurrency**: Limited by aiohttp (typically 100+ concurrent)
* **Network Concurrency**: Limited by ElectrumX server capacity
* **Memory Usage**: ~50-100MB base + connection overhead
* **CPU Usage**: Low to moderate, depends on request volume

Scalability
~~~~~~~~~~~

* **Horizontal**: Easy to scale by adding more instances
* **Vertical**: Limited by network I/O and ElectrumX server capacity
* **Bottlenecks**: Network latency and ElectrumX server performance

Caching Strategy
~~~~~~~~~~~~~~~~

* **Connection Pooling**: Persistent connections to ElectrumX servers
* **Heartbeat Monitoring**: Regular connection health checks
* **No Application Caching**: All requests go to backend (cache at client level if needed)

Monitoring Points
-----------------

Key Metrics
~~~~~~~~~~~~

* Request rate and response times
* Error rates by currency and method
* Connection status to ElectrumX servers
* Memory and CPU usage
* Heartbeat success rates

Health Checks
~~~~~~~~~~~~~

* ``GET /height`` - Service and backend connectivity
* ``POST /`` with ping - Basic service health
* ``GET /fees`` - Backend service functionality

Logging Strategy
~~~~~~~~~~~~~~~~

* Structured logging with timestamps and thread names
* Different log levels for different environments
* Error logging with full context
* Performance logging for slow operations

Security Considerations
-----------------------

Network Security
~~~~~~~~~~~~~~~~

* No built-in authentication (rely on network security)
* JSON-RPC over HTTP (consider HTTPS in production)
* Input validation and sanitization
* Rate limiting at proxy level

Data Security
~~~~~~~~~~~~~

* No sensitive data storage in the service
* Environment variables contain connection information
* Log sanitization to avoid sensitive data exposure

Container Security
~~~~~~~~~~~~~~~~~~

* Minimal base image (Python slim)
* No root user execution (planned enhancement)
* Regular security updates

Extensibility
-------------

Adding New Currencies
~~~~~~~~~~~~~~~~~~~~~

To add support for a new cryptocurrency:

1. Add currency symbol to ``allowed_currencies`` in ``ConfigurationManager``
2. Ensure ElectrumX server supports the currency
3. Test with the new currency configuration

Adding New RPC Methods
~~~~~~~~~~~~~~~~~~~~~~

To add new RPC methods:

1. Add method to appropriate handler class
2. Implement the method logic
3. Add method to ``switchcase`` dispatcher
4. Update API documentation

Customization Options
~~~~~~~~~~~~~~~~~~~~

* Custom error handling
* Custom logging formats
* Custom heartbeat intervals
* Custom timeout values

Limitations and Constraints
---------------------------

Current Limitations
~~~~~~~~~~~~~~~~~~~~

* No built-in authentication
* No application-level caching
* Limited to ElectrumX protocol
* No built-in rate limiting

Design Constraints
~~~~~~~~~~~~~~~~~~

* Maintain backward compatibility
* Thread-safe operation
* Minimal resource usage
* Simple deployment

Future Enhancements
~~~~~~~~~~~~~~~~~~~

* Built-in authentication
* Application-level caching
* Support for additional protocols
* Rate limiting and quotas
* Enhanced monitoring and metrics

For deployment guidance, see the :doc:`deployment` guide.