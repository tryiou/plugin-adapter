#!/usr/bin/env python3

import asyncio
import logging
from typing import Any, Optional, Union

from aiorpcx import connect_rs, timeout_after

from src.core.constants import ConfigConstants
from src.core.errors import NetworkError, ProtocolError
from src.utils.operation_logger import OperationLogger

logger = logging.getLogger(__name__)


class TCPSocket:
    """
    Thread-safe TCP socket wrapper for ElectrumX server communication.
    Provides connection management and RPC message sending capabilities.
    """

    def __init__(self, host: str, port: int, max_concurrent_connections: int = 3) -> None:
        """
        Initialize TCP socket connection parameters.
        
        Args:
            host: Server hostname or IP address
            port: Server port number
            max_concurrent_connections: Maximum concurrent connections per currency
        """
        self.host = host
        self.port = port
        self._session: Optional[Any] = None
        self._lock = asyncio.Lock()
        self._max_concurrent_connections = max_concurrent_connections

    async def connect(self) -> None:
        """
        Establish connection to the ElectrumX server.
        
        Raises:
            OSError: If connection fails due to network issues
            Exception: For any other connection errors
        """
        # Use instance-level semaphore to avoid class-level shared state
        semaphore = asyncio.Semaphore(self._max_concurrent_connections)

        async with semaphore:
            start = OperationLogger.start("connect", f"{self.host}:{self.port}")

            try:
                self._session = await connect_rs(self.host, self.port).__aenter__()
                self._session.transport._framer.max_size = 0

                # Identify client to ElectrumX server (required for newer servers)
                await self._session.send_request("server.version", ["plugin-adapter", "1.4"])

                OperationLogger.end("connect", start, f"{self.host}:{self.port}")

            except OSError as e:
                OperationLogger.error("connect", f"{self.host}:{self.port}", e)
                self._session = None
                raise NetworkError(f"Connection failed: {e.strerror}", e)
            except Exception as e:
                OperationLogger.error("connect", f"{self.host}:{self.port}", e)
                self._session = None
                raise NetworkError(f"Connection failed: {str(e)}", e)

    async def reconnect_if_closing(self) -> None:
        """Reconnect if the session is closed or doesn't exist."""
        async with self._lock:
            if self._session is None or self._session.is_closing():
                OperationLogger.start("reconnect", f"{self.host}:{self.port}")
                await self.connect()

    async def send_message(self, command: str, message: Any, timeout: int = ConfigConstants.TIMEOUT_DEFAULT) -> Union[
        int, Any]:
        """
        Send a single RPC message to the server.
        
        Args:
            command: RPC command name
            message: Command parameters
            timeout: Request timeout in seconds
            
        Returns:
            Server response
            
        Raises:
            NetworkError: If connection is lost
            ProtocolError: If request fails
        """
        # start = OperationLogger.start("send_message", f"{self.host}:{self.port}")

        await self.reconnect_if_closing()

        if self._session is None:
            OperationLogger.error("send_message", f"{self.host}:{self.port}",
                                  NetworkError("No active session available"))
            raise NetworkError("No active session available")

        try:
            async with timeout_after(timeout):
                result = await self._session.send_request(command, message)
                # OperationLogger.end("send_message", start, f"{self.host}:{self.port}")
                return result
        except OSError as e:
            OperationLogger.error("send_message", f"{self.host}:{self.port}", e)
            raise NetworkError(f"Connection lost: {str(e)}", e)
        except Exception as e:
            OperationLogger.error("send_message", f"{self.host}:{self.port}", e)
            raise ProtocolError(f"Request failed: {str(e)}", e)

    async def send_batch(self, command: str, message: Optional[list] = None,
                         timeout: int = ConfigConstants.TIMEOUT_DEFAULT) -> Union[int, Any]:
        """
        Send a batch of RPC messages to the server.
        
        Args:
            command: RPC command name
            message: List of command parameters
            timeout: Request timeout in seconds
            
        Returns:
            Server responses
            
        Raises:
            NetworkError: If connection is lost
            ProtocolError: If request fails
        """
        start = OperationLogger.start("send_batch", f"{self.host}:{self.port}")

        await self.reconnect_if_closing()

        if message is None or not isinstance(message, list):
            OperationLogger.error("send_batch", f"{self.host}:{self.port}", ProtocolError("Invalid message format"))
            raise ProtocolError("Invalid message format")

        try:
            async with timeout_after(ConfigConstants.TIMEOUT_DEFAULT):
                if self._session is None:
                    raise NetworkError("No active session available")
                async with self._session.send_batch() as batch:
                    for msg in message:
                        batch.add_request(command, [msg])

                result = batch.results
                OperationLogger.end("send_batch", start, f"{self.host}:{self.port}")
                return result
        except OSError as e:
            OperationLogger.error("send_batch", f"{self.host}:{self.port}", e)
            raise NetworkError(f"Connection lost: {str(e)}", e)
        except Exception as e:
            OperationLogger.error("send_batch", f"{self.host}:{self.port}", e)
            raise ProtocolError(f"Request failed: {str(e)}", e)

    @property
    def session(self) -> Optional[Any]:
        """Get the current session object."""
        return self._session

    async def close(self) -> None:
        """Close the socket connection."""
        # start = OperationLogger.start("close", f"{self.host}:{self.port}")

        async with self._lock:
            if self._session:
                try:
                    await self._session.close()
                    # Connection close logging handled by ConnectionManager
                except Exception as e:
                    OperationLogger.error("close", f"{self.host}:{self.port}", e)
                finally:
                    self._session = None
                    # Explicitly clean up references to help garbage collection
                    self._session = None

            # OperationLogger.end("close", start, f"{self.host}:{self.port}")

    @property
    def is_connected(self) -> bool:
        """Check if the socket is currently connected."""
        return self._session is not None and not self._session.is_closing()
