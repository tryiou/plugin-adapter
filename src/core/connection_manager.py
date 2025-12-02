#!/usr/bin/env python3

import asyncio
import logging
from typing import Dict

from src.core.configuration import config_manager
from src.core.constants import ConfigConstants
from src.core.errors import NetworkError, ProtocolError
from src.networking.tcp_socket import TCPSocket
from src.utils.operation_logger import OperationLogger

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Centralized connection manager that handles all TCP socket connections.
    Provides automatic reconnection, connection pooling, and consistent error handling.
    """

    def __init__(self, max_concurrent_connections: int = 3):
        """Initialize the connection manager with thread-safe state."""
        self._sockets: Dict[str, TCPSocket] = {}
        self._lock = asyncio.Lock()
        self._max_concurrent_connections = max_concurrent_connections
        # Per-currency connection semaphores to prevent connection storms
        self._currency_semaphores: Dict[str, asyncio.Semaphore] = {}
        self._shutdown = False

    async def get_socket(self, currency: str) -> TCPSocket:
        """
        Get or create a socket connection for a currency with automatic reconnection.
        
        Args:
            currency: Currency symbol (e.g., "BTC", "LTC")
            
        Returns:
            Connected TCPSocket instance
            
        Raises:
            NetworkError: If connection fails
            ProtocolError: If currency is not configured
        """
        # Prevent new connections during shutdown
        if self._shutdown:
            raise NetworkError(f"Cannot create new connection for {currency}: ConnectionManager is shutting down")

        # Use lock to prevent multiple coroutines from creating connections concurrently
        async with self._lock:
            # Check if we already have a connected socket
            socket = self._sockets.get(currency)
            if socket and socket.is_connected:
                OperationLogger.debug_connection(socket.host, socket.port, "reused")
                return socket

            # Need to create or reconnect - lock is held during the entire process
            # Get or create per-currency semaphore to prevent connection storms
            semaphore = await self._get_or_create_semaphore(currency)

            # Use semaphore to limit concurrent connections for this currency
            async with semaphore:
                # Check again if socket was created while waiting for semaphore
                # This prevents multiple connections when multiple coroutines are waiting
                socket = self._sockets.get(currency)
                if socket and socket.is_connected:
                    OperationLogger.debug_connection(socket.host, socket.port, "reused")
                    return socket

                # Get configuration
                coin_config = config_manager.get_coin_config(currency)
                if not coin_config:
                    raise ProtocolError(f"No configuration found for currency: {currency}")

                # Close existing socket if it exists but is disconnected
                if currency in self._sockets:
                    try:
                        await self._sockets[currency].close()
                    except Exception as e:
                        OperationLogger.debug_error("close_existing_socket", currency, e)

                # Create new connection
                try:
                    socket = TCPSocket(
                        coin_config.host,
                        coin_config.port + ConfigConstants.ELECTRUM_RPC_PORT_OFFSET,
                        max_concurrent_connections=self._max_concurrent_connections
                    )
                    await socket.connect()

                    # Store the socket immediately to prevent race conditions
                    self._sockets[currency] = socket
                    OperationLogger.debug_connection(socket.host, socket.port, "established")
                    # Log success at INFO level for production
                    OperationLogger.success("connect", currency, 0,
                                            {"currency": currency, "host": socket.host, "port": socket.port})

                    return socket

                except Exception as e:
                    OperationLogger.debug_error("connect", currency, e)
                    OperationLogger.debug_connection(coin_config.host,
                                                     coin_config.port + ConfigConstants.ELECTRUM_RPC_PORT_OFFSET,
                                                     "failed")
                    # Log failure at INFO level for production
                    OperationLogger.success("connect", currency, 0,
                                            {"currency": currency, "success": False, "error": str(e)})
                    raise NetworkError(f"Failed to connect to {currency}: {e}")

    async def reconnect(self, currency: str) -> TCPSocket:
        """
        Force reconnection for a specific currency.
        
        Args:
            currency: Currency symbol
            
        Returns:
            New connected TCPSocket instance
            
        Raises:
            NetworkError: If reconnection fails
        """
        start = OperationLogger.start("reconnect", currency)

        # Get configuration for logging
        coin_config = config_manager.get_coin_config(currency)
        if coin_config:
            OperationLogger.debug_connection(coin_config.host,
                                             coin_config.port + ConfigConstants.ELECTRUM_RPC_PORT_OFFSET,
                                             "reconnect_attempt")

        try:
            # Force reconnection by removing existing socket and calling get_socket
            if currency in self._sockets:
                try:
                    await self._sockets[currency].close()
                except Exception as e:
                    OperationLogger.debug_error("close_existing_socket", currency, e)
                del self._sockets[currency]

            result = await self.get_socket(currency)
            OperationLogger.end("reconnect", start, currency)
            return result
        except Exception as e:
            OperationLogger.debug_error("reconnect", currency, e)
            raise

    async def heartbeat(self, currency: str) -> bool:
        """
        Perform a lightweight heartbeat check for a currency using existing connection.
        
        Args:
            currency: Currency symbol
            
        Returns:
            True if heartbeat successful, False otherwise
        """
        start = OperationLogger.start("heartbeat", currency)

        try:
            socket = await self.get_socket(currency)
            # Use existing socket for ping - this is much more efficient than creating new connections
            await socket.send_message("server.ping", [], timeout=ConfigConstants.TIMEOUT_HEARTBEAT)
            OperationLogger.end("heartbeat", start, currency)
            return True
        except Exception as e:
            OperationLogger.debug_error("heartbeat", currency, e)
            # Don't automatically reconnect on heartbeat failure - let the next request handle it
            return False

    async def get_connection_info(self) -> Dict[str, Dict[str, str]]:
        """
        Get information about all current connections.
        
        Returns:
            Dictionary mapping currencies to connection status
        """
        async with self._lock:
            info = {}
            for currency, socket in self._sockets.items():
                info[currency] = {
                    'connected': str(socket.is_connected),
                    'host': socket.host,
                    'port': str(socket.port)
                }
            return info

    def is_connected(self, currency: str) -> bool:
        """
        Check if a currency has an active connection.
        
        Args:
            currency: Currency symbol
            
        Returns:
            True if connected, False otherwise
        """
        socket = self._sockets.get(currency)
        return socket is not None and socket.is_connected

    async def _get_or_create_semaphore(self, currency: str) -> asyncio.Semaphore:
        """
        Get or create a semaphore for limiting concurrent connections per currency.
        
        Args:
            currency: Currency symbol
            
        Returns:
            Semaphore instance for the currency
        """
        if currency not in self._currency_semaphores:
            # Create semaphore for this currency to prevent connection storms
            self._currency_semaphores[currency] = asyncio.Semaphore(self._max_concurrent_connections)
        return self._currency_semaphores[currency]

    async def close_all(self) -> None:
        """Enhanced connection cleanup with timeout."""
        async with self._lock:
            # Set shutdown flag to prevent new connections
            self._shutdown = True

            # Close all sockets IMMEDIATELY - skip timeouts during shutdown
            cleanup_tasks = []
            for currency, socket in list(self._sockets.items()):
                if socket and socket.is_connected:
                    # Create task for cleanup to allow cancellation
                    cleanup_tasks.append(asyncio.create_task(self._close_socket_with_timeout(currency, socket)))

            if cleanup_tasks:
                # IMMEDIATE EXIT - don't wait for connections to close
                # Just cancel all cleanup tasks and exit immediately
                for task in cleanup_tasks:
                    if hasattr(task, 'cancel'):
                        task.cancel()

            # Clear all references immediately
            self._sockets.clear()
            self._currency_semaphores.clear()

    async def _close_socket_with_timeout(self, currency: str, socket) -> None:
        """Close a socket with timeout."""
        start = OperationLogger.start("close_socket", currency)

        try:
            # IMMEDIATE EXIT - skip timeout during shutdown
            await socket.close()
            OperationLogger.end("close_socket", start, currency)
            OperationLogger.debug_connection(socket.host, socket.port, "closed")
        except asyncio.TimeoutError:
            OperationLogger.debug_error("close_socket", currency, Exception("Timeout closing socket"))
            OperationLogger.debug_connection(socket.host, socket.port, "close_timeout")
        except Exception as e:
            OperationLogger.debug_error("close_socket", currency, e)
            OperationLogger.debug_connection(socket.host, socket.port, "close_error")

    def shutdown(self) -> None:
        """Set shutdown flag to prevent new connections."""
        self._shutdown = True
