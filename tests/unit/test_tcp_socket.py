#!/usr/bin/env python3
"""
Unit tests for TCP socket module.
Tests cover basic TCP socket functionality with proper mocking.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.errors import NetworkError, ProtocolError
from src.networking.tcp_socket import TCPSocket
from tests.unit.test_helpers import (create_mock_batch, create_mock_session,
                                     mock_connect_rs_with_session)


class TestTCPSocket:
    """Test suite for TCPSocket class."""

    def setup_method(self):
        """Setup for each test method."""
        self.socket = TCPSocket("localhost", 8000)

    def teardown_method(self):
        """Cleanup after each test method."""
        # Clean up session if exists
        if hasattr(self.socket, '_session') and self.socket._session:
            self.socket._session = None

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful TCP connection."""
        mock_session = create_mock_session(is_closing=False)

        with mock_connect_rs_with_session(mock_session):
            await self.socket.connect()

            assert self.socket.is_connected is True
            assert self.socket._session == mock_session
            mock_session.send_request.assert_called_once_with("server.version", ["plugin-adapter", "1.4"])

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test TCP connection failure."""
        # Mock the aiorpcx.connect_rs function to raise an OSError
        mock_connect_rs = AsyncMock()
        mock_connect_rs.__aenter__ = AsyncMock(side_effect=OSError("Connection failed"))
        mock_connect_rs.__aexit__ = AsyncMock(return_value=None)

        with patch('src.networking.tcp_socket.connect_rs', return_value=mock_connect_rs):
            with pytest.raises(NetworkError):
                await self.socket.connect()

            assert self.socket.is_connected is False

    @pytest.mark.asyncio
    async def test_close(self):
        """Test TCP socket closure."""
        mock_session = AsyncMock()
        mock_session.is_closing.return_value = False
        self.socket._session = mock_session

        await self.socket.close()

        mock_session.close.assert_called_once()
        assert self.socket._session is None
        assert self.socket.is_connected is False

    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """Test successful message sending."""
        mock_session = create_mock_session(is_closing=False)

        with mock_connect_rs_with_session(mock_session):
            self.socket._session = mock_session

            command = "blockchain.scripthash.get_balance"
            message = ["abc123"]
            result = await self.socket.send_message(command, message)

            mock_session.send_request.assert_called_with(command, message)
            assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_send_message_not_connected(self):
        """Test sending message when not connected."""
        command = "blockchain.scripthash.get_balance"
        message = ["abc123"]

        with pytest.raises(NetworkError):
            await self.socket.send_message(command, message)

    @pytest.mark.asyncio
    async def test_send_message_connection_lost(self):
        """Test sending message when connection is lost."""
        mock_session = AsyncMock()
        mock_session.is_closing.return_value = True
        self.socket._session = mock_session

        command = "blockchain.scripthash.get_balance"
        message = ["abc123"]

        with pytest.raises(NetworkError):
            await self.socket.send_message(command, message)

    @pytest.mark.asyncio
    async def test_send_message_timeout(self):
        """Test sending message with timeout."""
        mock_session = AsyncMock()
        mock_session.is_closing.return_value = False
        mock_session.send_request = AsyncMock(side_effect=asyncio.TimeoutError())
        self.socket._session = mock_session

        command = "blockchain.scripthash.get_balance"
        message = ["abc123"]

        with pytest.raises(NetworkError):
            await self.socket.send_message(command, message)

    @pytest.mark.asyncio
    async def test_send_batch_success(self):
        """Test successful batch message sending."""
        mock_session = create_mock_session(is_closing=False)
        mock_batch = create_mock_batch()

        # Mock the send_batch method to return the mock batch
        mock_session.send_batch = MagicMock(return_value=mock_batch)
        self.socket._session = mock_session

        command = "blockchain.scripthash.get_balance"
        messages = [["abc123"], ["def456"]]

        result = await self.socket.send_batch(command, messages)

        mock_session.send_batch.assert_called_once()
        assert mock_batch.add_request.call_count == 2
        mock_batch.add_request.assert_any_call(command, [["abc123"]])
        mock_batch.add_request.assert_any_call(command, [["def456"]])
        assert result == [{"result": "success1"}, {"result": "success2"}]

    @pytest.mark.asyncio
    async def test_send_batch_not_connected(self):
        """Test sending batch when not connected."""
        command = "blockchain.scripthash.get_balance"
        messages = [["abc123"], ["def456"]]

        with pytest.raises(NetworkError):
            await self.socket.send_batch(command, messages)

    @pytest.mark.asyncio
    async def test_send_batch_invalid_message(self):
        """Test sending batch with invalid message format."""
        command = "blockchain.scripthash.get_balance"

        # Mock reconnect_if_closing to avoid triggering reconnection
        with patch.object(self.socket, 'reconnect_if_closing'):
            # Test with None message
            with pytest.raises(ProtocolError):
                await self.socket.send_batch(command, None)

            # Test with non-list message
            with pytest.raises(ProtocolError):
                await self.socket.send_batch(command, "invalid")

    @pytest.mark.asyncio
    async def test_send_batch_timeout(self):
        """Test sending batch with timeout."""
        mock_session = create_mock_session(is_closing=False)

        # Create a proper mock batch that matches aiorpcx interface
        mock_batch = AsyncMock()
        mock_batch.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_batch.__aexit__ = AsyncMock(return_value=None)

        # Mock the send_batch method to return the mock batch
        mock_session.send_batch = MagicMock(return_value=mock_batch)
        self.socket._session = mock_session

        command = "blockchain.scripthash.get_balance"
        messages = [["abc123"], ["def456"]]

        with pytest.raises(NetworkError):
            await self.socket.send_batch(command, messages)

    def test_socket_properties(self):
        """Test socket property access."""
        assert self.socket.host == "localhost"
        assert self.socket.port == 8000
        assert self.socket.is_connected is False

    @pytest.mark.asyncio
    async def test_connection_state_management(self):
        """Test connection state management."""
        # Initially not connected
        assert self.socket.is_connected is False

        # After connection
        mock_session = create_mock_session(is_closing=False)

        with mock_connect_rs_with_session(mock_session):
            await self.socket.connect()
            assert self.socket.is_connected is True

        # After closure
        await self.socket.close()
        assert self.socket.is_connected is False

    @pytest.mark.asyncio
    async def test_reconnect_if_closing(self):
        """Test automatic reconnection when session is closing."""
        mock_session = create_mock_session(is_closing=True)
        self.socket._session = mock_session

        mock_new_session = create_mock_session(is_closing=False)

        with mock_connect_rs_with_session(mock_new_session):
            await self.socket.reconnect_if_closing()

            assert self.socket.is_connected is True
            assert self.socket._session == mock_new_session

    @pytest.mark.asyncio
    async def test_send_message_with_reconnect(self):
        """Test that send_message triggers reconnection if needed."""
        mock_session = create_mock_session(is_closing=True)
        mock_session.send_request = AsyncMock(return_value={"result": "success"})
        self.socket._session = mock_session

        command = "blockchain.scripthash.get_balance"
        message = ["abc123"]

        mock_new_session = create_mock_session(is_closing=False)

        with mock_connect_rs_with_session(mock_new_session):
            result = await self.socket.send_message(command, message)

            assert result == {"result": "success"}
            assert self.socket.is_connected is True
