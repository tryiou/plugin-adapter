class ConfigConstants:
    """
    Centralized configuration constants for the application.
    
    This class provides a single source of truth for all configuration constants,
    making them easier to manage and modify.
    """

    # Timeout constants for different operation types
    TIMEOUT_HEARTBEAT = 5  # Fast operations
    TIMEOUT_BLOCK_COUNT = 2  # Fast operations
    TIMEOUT_FEES = 2  # Fast operations
    TIMEOUT_BALANCE = 10  # Medium operations
    TIMEOUT_TRANSACTIONS = 10  # Medium operations
    TIMEOUT_HISTORY = 30  # Slow operations
    TIMEOUT_UTXO = 30  # Slow operations
    TIMEOUT_DEFAULT = 30  # Default timeout

    # Port constants
    DEFAULT_ELECTRUM_PORT = 8000  # Default ElectrumX server port
    ELECTRUM_RPC_PORT_OFFSET = 1000  # Offset for RPC port (8000 + 1000 = 9000)

    # Server constants
    DEFAULT_SERVER_PORT = 5000  # Default web server port

    # Timestamp constants
    UNIX_EPOCH_YEAR = 1970  # Unix epoch start year


class ShutdownConstants:
    """Shutdown timeout constants for proper cleanup."""

    # Total shutdown timeout
    SHUTDOWN_TIMEOUT = 5.0

    # Individual connection timeout during cleanup
    CONNECTION_TIMEOUT = 2.0

    # Task cancellation timeout
    TASK_CANCELLATION_TIMEOUT = 3.0
