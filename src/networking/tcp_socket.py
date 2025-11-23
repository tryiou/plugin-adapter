#!/usr/bin/env python3

import asyncio
import logging
from aiorpcx import connect_rs, timeout_after
from typing import Optional, Any, Union

logger = logging.getLogger(__name__)

# Error constants - replaced with proper error classes in error_handling.py
OS_ERROR = -1
OTHER_EXCEPTION = -2


class TCPSocket:
    """
    Thread-safe TCP socket wrapper for ElectrumX server communication.
    Provides connection management and RPC message sending capabilities.
    """

    def __init__(self, host: str, port: int) -> None:
        """
        Initialize TCP socket connection parameters.
        
        Args:
            host: Server hostname or IP address
            port: Server port number
        """
        self.host = host
        self.port = port
        self._session: Optional[Any] = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """
        Establish connection to the ElectrumX server.
        
        Raises:
            OSError: If connection fails due to network issues
            Exception: For any other connection errors
        """
        try:
            self._session = await connect_rs(self.host, self.port).__aenter__()
            self._session.transport._framer.max_size = 0
            logger.debug(f"[client] Successfully connected to {self.host}:{self.port}")
        except OSError as e:
            logger.error(f"[client] ERROR: Connection error to {self.host}:{self.port} - {e.strerror}")
            self._session = None
            raise
        except Exception as e:
            logger.error(f"[client] ERROR: Error connecting! {str(e)}")
            self._session = None
            raise

    async def reconnect_if_closing(self) -> None:
        """Reconnect if the session is closed or doesn't exist."""
        async with self._lock:
            session_state = "None" if self._session is None else f"Closing: {self._session.is_closing()}, Connected: {not self._session.is_closing()}"
            logger.debug(f"[client] {self.host}:{self.port} - reconnect_if_closing called. Session state: {session_state}")
            
            if self._session is None or self._session.is_closing():
                logger.info(f"[client] {self.host}:{self.port} - Reconnecting socket (None: {self._session is None}, Closing: {self._session.is_closing() if self._session else 'N/A'})")
                await self.connect()

    async def send_message(self, command: str, message: Any, timeout: int = 30) -> Union[int, Any]:
        """
        Send a single RPC message to the server.
        
        Args:
            command: RPC command name
            message: Command parameters
            timeout: Request timeout in seconds
            
        Returns:
            Server response or error code (-1 for OS error, -2 for other exceptions)
        """
        await self.reconnect_if_closing()

        if self._session is None:
            return OTHER_EXCEPTION

        try:
            async with timeout_after(timeout):
                return await self._session.send_request(command, message)
        except OSError:
            logger.error(
                f"[client] ERROR: Could not connect! Is the Electrum X server running on port {self.port}?"
            )
            return OS_ERROR
        except Exception as e:
            logger.error(f"[client] ERROR: Error sending request! {str(e)}")
            return OTHER_EXCEPTION

    async def send_batch(self, command: str, message: Optional[list] = None, timeout: int = 30) -> Union[int, Any]:
        """
        Send a batch of RPC messages to the server.
        
        Args:
            command: RPC command name
            message: List of command parameters
            timeout: Request timeout in seconds
            
        Returns:
            Server responses or error code (-1 for OS error, -2 for other exceptions)
        """
        await self.reconnect_if_closing()

        if message is None or not isinstance(message, list):
            return OTHER_EXCEPTION

        try:
            async with timeout_after(timeout):
                async with self._session.send_batch() as batch:
                    for msg in message:
                        batch.add_request(command, [msg])

                return batch.results
        except OSError:
            logger.error(
                f"[client] ERROR: Could not connect! Is the Electrum X server running on port {self.port}?"
            )
            return OS_ERROR
        except Exception as e:
            logger.error(f"[client] ERROR: Error sending request! {str(e)}")
            return OTHER_EXCEPTION

    @property
    def session(self) -> Optional[Any]:
        """Get the current session object."""
        return self._session

    @property
    def is_connected(self) -> bool:
        """Check if the socket is currently connected."""
        return self._session is not None and not self._session.is_closing()
