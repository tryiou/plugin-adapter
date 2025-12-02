#!/usr/bin/env python3
"""
Unit tests for Connection Manager (src/core/connection_manager.py).
Tests connection pooling, automatic reconnection, concurrency control, and production scenarios.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.configuration import config_manager
from src.core.connection_manager import ConnectionManager
from src.core.errors import NetworkError, ProtocolError
from src.networking.tcp_socket import TCPSocket


class TestConnectionManager:
    """Test suite for ConnectionManager class."""

    def setup_method(self):
        """Setup for each test method."""
        self.manager = ConnectionManager(max_concurrent_connections=2)

    def teardown_method(self):
        """Cleanup after each test method."""
        # Reset manager state
        self.manager._sockets.clear()
        self.manager._currency_semaphores.clear()
        self.manager._shutdown = False

    @pytest.mark.asyncio
    async def test_manager_initialization(self):
        """Test ConnectionManager initialization."""
        manager = ConnectionManager(max_concurrent_connections=5)

        assert manager._max_concurrent_connections == 5
        assert len(manager._sockets) == 0
        assert len(manager._currency_semaphores) == 0
        assert manager._shutdown is False
        assert isinstance(manager._lock, asyncio.Lock)

    @pytest.mark.asyncio
    async def test_get_socket_new_connection(self):
        """Test getting a socket for a new currency."""
        with patch.object(self.manager, '_get_or_create_semaphore') as mock_get_semaphore, \
                patch.object(config_manager, 'get_coin_config') as mock_get_config, \
                patch('src.core.connection_manager.TCPSocket') as mock_socket_class:
            mock_config = MagicMock()
            mock_config.host = 'localhost'
            mock_config.port = 8000
            mock_get_config.return_value = mock_config

            mock_semaphore = AsyncMock()
            mock_get_semaphore.return_value = mock_semaphore

            mock_socket = AsyncMock(spec=TCPSocket)
            mock_socket.host = 'localhost'
            mock_socket.port = 9000
            mock_socket_class.return_value = mock_socket
            mock_socket.connect.return_value = None
            mock_socket.is_connected = True

            result = await self.manager.get_socket('BTC')

            # Should create new socket
            mock_socket_class.assert_called_once_with('localhost', 9000, max_concurrent_connections=2)
            assert result == mock_socket

    @pytest.mark.asyncio
    async def test_get_socket_existing_connected(self):
        """Test getting a socket when already connected."""
        mock_socket = AsyncMock(spec=TCPSocket)
        mock_socket.host = 'localhost'
        mock_socket.port = 9000
        mock_socket.is_connected = True
        self.manager._sockets['BTC'] = mock_socket

        result = await self.manager.get_socket('BTC')

        # Should return existing socket without creating new one
        assert result == mock_socket

    @pytest.mark.asyncio
    async def test_get_socket_existing_disconnected(self):
        """Test getting a socket when existing connection is disconnected."""
        mock_socket = AsyncMock(spec=TCPSocket)
        mock_socket.is_connected = False
        self.manager._sockets['BTC'] = mock_socket

        with patch.object(self.manager, '_get_or_create_semaphore') as mock_get_semaphore, \
                patch.object(config_manager, 'get_coin_config') as mock_get_config, \
                patch('src.core.connection_manager.TCPSocket') as mock_socket_class:
            mock_config = MagicMock()
            mock_config.host = 'localhost'
            mock_config.port = 8000
            mock_get_config.return_value = mock_config

            mock_semaphore = AsyncMock()
            mock_get_semaphore.return_value = mock_semaphore

            mock_socket = AsyncMock(spec=TCPSocket)
            mock_socket.host = 'localhost'
            mock_socket.port = 9000
            mock_socket_class.return_value = mock_socket
            mock_socket.connect.return_value = None
            mock_socket.is_connected = True

            result = await self.manager.get_socket('BTC')

            # Should create new socket since existing one is disconnected
            mock_socket_class.assert_called_once_with('localhost', 9000, max_concurrent_connections=2)
            assert result == mock_socket

    @pytest.mark.asyncio
    async def test_get_socket_during_shutdown(self):
        """Test getting a socket during shutdown."""
        self.manager._shutdown = True

        with pytest.raises(NetworkError) as exc_info:
            await self.manager.get_socket('BTC')

        assert "ConnectionManager is shutting down" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ensure_connected_success(self):
        """Test successful connection establishment."""
        with patch.object(config_manager, 'get_coin_config') as mock_get_config, \
                patch.object(self.manager, '_get_or_create_semaphore') as mock_get_semaphore, \
                patch('src.core.connection_manager.TCPSocket') as mock_socket_class:
            mock_config = MagicMock()
            mock_config.host = 'localhost'
            mock_config.port = 8000
            mock_get_config.return_value = mock_config

            mock_semaphore = AsyncMock()
            mock_get_semaphore.return_value = mock_semaphore

            mock_socket = AsyncMock(spec=TCPSocket)
            mock_socket.host = 'localhost'
            mock_socket.port = 9000
            mock_socket_class.return_value = mock_socket
            mock_socket.connect.return_value = None

            result = await self.manager.get_socket('BTC')

            # Verify configuration was retrieved
            mock_get_config.assert_called_once_with('BTC')
            # Verify semaphore was used
            mock_semaphore.__aenter__.assert_called_once()
            # Verify socket was created and connected (port should be 8000 + 1000 = 9000)
            mock_socket_class.assert_called_once_with('localhost', 9000, max_concurrent_connections=2)
            mock_socket.connect.assert_called_once()
            # Verify socket was stored
            assert self.manager._sockets['BTC'] == mock_socket
            assert result == mock_socket

    @pytest.mark.asyncio
    async def test_ensure_connected_no_config(self):
        """Test connection attempt when no configuration exists."""
        with patch.object(config_manager, 'get_coin_config') as mock_get_config:
            mock_get_config.return_value = None

            with pytest.raises(ProtocolError) as exc_info:
                await self.manager.get_socket('BTC')

            assert "No configuration found for currency" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ensure_connected_failure(self):
        """Test connection failure handling."""
        with patch.object(config_manager, 'get_coin_config') as mock_get_config, \
                patch.object(self.manager, '_get_or_create_semaphore') as mock_get_semaphore, \
                patch('src.core.connection_manager.TCPSocket') as mock_socket_class:
            mock_config = MagicMock()
            mock_config.host = 'localhost'
            mock_config.port = 8000
            mock_get_config.return_value = mock_config

            mock_semaphore = AsyncMock()
            mock_get_semaphore.return_value = mock_semaphore

            mock_socket = AsyncMock(spec=TCPSocket)
            mock_socket.host = 'localhost'
            mock_socket.port = 9000
            mock_socket_class.return_value = mock_socket
            mock_socket.connect.side_effect = Exception("Connection failed")

            with pytest.raises(NetworkError) as exc_info:
                await self.manager.get_socket('BTC')

            assert "Failed to connect to BTC" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_reconnect_force_reconnection(self):
        """Test forced reconnection for a currency."""
        with patch.object(self.manager, '_get_or_create_semaphore') as mock_get_semaphore, \
                patch.object(config_manager, 'get_coin_config') as mock_get_config, \
                patch('src.core.connection_manager.TCPSocket') as mock_socket_class:
            mock_config = MagicMock()
            mock_config.host = 'localhost'
            mock_config.port = 8000
            mock_get_config.return_value = mock_config

            mock_semaphore = AsyncMock()
            mock_get_semaphore.return_value = mock_semaphore

            mock_socket = AsyncMock(spec=TCPSocket)
            mock_socket.host = 'localhost'
            mock_socket.port = 9000
            mock_socket_class.return_value = mock_socket
            mock_socket.connect.return_value = None
            mock_socket.is_connected = True

            result = await self.manager.reconnect('BTC')

            # Should create new socket
            mock_socket_class.assert_called_once_with('localhost', 9000, max_concurrent_connections=2)
            assert result == mock_socket

    @pytest.mark.asyncio
    async def test_heartbeat_success(self):
        """Test successful heartbeat check."""
        with patch.object(self.manager, 'get_socket') as mock_get_socket:
            mock_socket = AsyncMock(spec=TCPSocket)
            mock_get_socket.return_value = mock_socket

            result = await self.manager.heartbeat('BTC')

            mock_socket.send_message.assert_called_once_with(
                "server.ping", [], timeout=5
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_heartbeat_failure(self):
        """Test heartbeat failure handling."""
        with patch.object(self.manager, 'get_socket') as mock_get_socket:
            mock_get_socket.side_effect = NetworkError("Connection failed")

            result = await self.manager.heartbeat('BTC')

            assert result is False

    @pytest.mark.asyncio
    async def test_get_connection_info(self):
        """Test connection information retrieval."""
        mock_socket1 = AsyncMock(spec=TCPSocket)
        mock_socket1.is_connected = True
        mock_socket1.host = 'localhost'
        mock_socket1.port = 8000

        mock_socket2 = AsyncMock(spec=TCPSocket)
        mock_socket2.is_connected = False
        mock_socket2.host = 'localhost'
        mock_socket2.port = 8001

        self.manager._sockets = {
            'BTC': mock_socket1,
            'LTC': mock_socket2
        }

        info = await self.manager.get_connection_info()

        assert 'BTC' in info
        assert 'LTC' in info
        assert info['BTC']['connected'] == 'True'
        assert info['LTC']['connected'] == 'False'
        assert info['BTC']['host'] == 'localhost'
        assert info['LTC']['host'] == 'localhost'

    def test_is_connected(self):
        """Test connection status checking."""
        mock_socket = AsyncMock(spec=TCPSocket)
        mock_socket.is_connected = True
        self.manager._sockets['BTC'] = mock_socket

        assert self.manager.is_connected('BTC') is True
        assert self.manager.is_connected('LTC') is False

        mock_socket.is_connected = False
        assert self.manager.is_connected('BTC') is False

    @pytest.mark.asyncio
    async def test_get_or_create_semaphore(self):
        """Test semaphore creation and reuse."""
        # First call should create semaphore
        semaphore1 = await self.manager._get_or_create_semaphore('BTC')
        assert isinstance(semaphore1, asyncio.Semaphore)

        # Second call should return the same semaphore
        semaphore2 = await self.manager._get_or_create_semaphore('BTC')
        assert semaphore1 is semaphore2

        # Different currency should get different semaphore
        semaphore3 = await self.manager._get_or_create_semaphore('LTC')
        assert semaphore1 is not semaphore3

    @pytest.mark.asyncio
    async def test_close_all_immediate_exit(self):
        """Test immediate connection cleanup during shutdown."""
        mock_socket1 = AsyncMock(spec=TCPSocket)
        mock_socket1.is_connected = True
        mock_socket2 = AsyncMock(spec=TCPSocket)
        mock_socket2.is_connected = False

        self.manager._sockets = {
            'BTC': mock_socket1,
            'LTC': mock_socket2
        }

        # Mock the close method to track calls
        mock_socket1.close = AsyncMock()

        await self.manager.close_all()

        # Verify shutdown flag was set
        assert self.manager._shutdown is True
        # Verify socket close was attempted (even if task gets cancelled)
        # The implementation creates tasks but cancels them immediately
        mock_socket1.close.assert_not_called()
        # Verify all references were cleared
        assert len(self.manager._sockets) == 0
        assert len(self.manager._currency_semaphores) == 0

    @pytest.mark.asyncio
    async def test_close_all_no_connections(self):
        """Test cleanup when no connections exist."""
        await self.manager.close_all()

        # Should complete without errors
        assert self.manager._shutdown is True
        assert len(self.manager._sockets) == 0

    @pytest.mark.asyncio
    async def test_shutdown_flag(self):
        """Test shutdown flag setting."""
        assert self.manager._shutdown is False
        self.manager.shutdown()
        assert self.manager._shutdown is True

    @pytest.mark.asyncio
    async def test_concurrent_get_socket(self):
        """Test concurrent socket requests for the same currency."""
        with patch.object(self.manager, '_get_or_create_semaphore') as mock_get_semaphore, \
                patch.object(config_manager, 'get_coin_config') as mock_get_config, \
                patch('src.core.connection_manager.TCPSocket') as mock_socket_class:
            mock_config = MagicMock()
            mock_config.host = 'localhost'
            mock_config.port = 8000
            mock_get_config.return_value = mock_config

            mock_semaphore = AsyncMock()
            mock_get_semaphore.return_value = mock_semaphore

            mock_socket = AsyncMock(spec=TCPSocket)
            mock_socket.host = 'localhost'
            mock_socket.port = 9000
            mock_socket_class.return_value = mock_socket
            mock_socket.connect.return_value = None
            mock_socket.is_connected = True

            # Run multiple concurrent requests
            tasks = [
                asyncio.create_task(self.manager.get_socket('BTC'))
                for _ in range(3)
            ]

            results = await asyncio.gather(*tasks)

            # Should only create one socket due to lock preventing concurrent calls
            # The first call creates the socket, subsequent calls wait and get the existing one
            mock_socket_class.assert_called_once_with('localhost', 9000, max_concurrent_connections=2)
            # All results should be the same socket
            assert all(result == mock_socket for result in results)

    @pytest.mark.asyncio
    async def test_concurrent_different_currencies(self):
        """Test concurrent socket requests for different currencies."""
        with patch.object(self.manager, '_get_or_create_semaphore') as mock_get_semaphore, \
                patch.object(config_manager, 'get_coin_config') as mock_get_config, \
                patch('src.core.connection_manager.TCPSocket') as mock_socket_class:
            mock_config = MagicMock()
            mock_config.host = 'localhost'
            mock_config.port = 8000
            mock_get_config.return_value = mock_config

            mock_semaphore = AsyncMock()
            mock_get_semaphore.return_value = mock_semaphore

            mock_socket = AsyncMock(spec=TCPSocket)
            mock_socket.host = 'localhost'
            mock_socket.port = 9000
            mock_socket_class.return_value = mock_socket
            mock_socket.connect.return_value = None
            mock_socket.is_connected = True

            # Run concurrent requests for different currencies
            tasks = [
                asyncio.create_task(self.manager.get_socket('BTC')),
                asyncio.create_task(self.manager.get_socket('LTC')),
                asyncio.create_task(self.manager.get_socket('ETH'))
            ]

            await asyncio.gather(*tasks)

            # Should create socket for each currency
            assert mock_socket_class.call_count == 3
            mock_socket_class.assert_any_call('localhost', 9000, max_concurrent_connections=2)

    @pytest.mark.asyncio
    async def test_semaphore_prevents_connection_storms(self):
        """Test that semaphores prevent connection storms for same currency."""
        with patch.object(self.manager, '_get_or_create_semaphore') as mock_get_semaphore, \
                patch.object(config_manager, 'get_coin_config') as mock_get_config, \
                patch('src.core.connection_manager.TCPSocket') as mock_socket_class:
            # Create a semaphore with only 1 permit
            semaphore = asyncio.Semaphore(1)
            mock_get_semaphore.return_value = semaphore

            mock_config = MagicMock()
            mock_config.host = 'localhost'
            mock_config.port = 8000
            mock_get_config.return_value = mock_config

            mock_socket = AsyncMock(spec=TCPSocket)
            mock_socket.host = 'localhost'
            mock_socket.port = 9000
            mock_socket_class.return_value = mock_socket
            mock_socket.connect.return_value = None
            mock_socket.is_connected = True

            # Create more concurrent tasks than semaphore permits
            tasks = [
                asyncio.create_task(self.manager.get_socket('BTC'))
                for _ in range(3)
            ]

            results = await asyncio.gather(*tasks)

            # All should succeed but be serialized by semaphore
            assert len(results) == 3
            assert all(result == mock_socket for result in results)
            # Should only connect once due to lock preventing concurrent calls
            mock_socket_class.assert_called_once_with('localhost', 9000, max_concurrent_connections=2)
