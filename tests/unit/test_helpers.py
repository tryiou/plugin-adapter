#!/usr/bin/env python3
"""
Test helpers for TCP socket testing.
Provides common mocking utilities and constants for consistent test setup.
"""

from unittest.mock import AsyncMock, MagicMock, patch

# Mock patch location for aiorpcx.connect_rs
AIORPCX_CONNECT_RS_PATCH = 'src.networking.tcp_socket.connect_rs'


def create_mock_session(is_closing=False, server_version_response=None):
    """
    Create a properly configured mock session that matches aiorpcx interface.
    
    Args:
        is_closing (bool): Whether the session is closing
        server_version_response (list): Response for server.version call
        
    Returns:
        AsyncMock: Configured mock session
    """
    if server_version_response is None:
        server_version_response = ["mock-server", "1.4"]

    mock_session = AsyncMock()
    # Mock the is_closing method as a callable that returns the boolean
    mock_session.is_closing = MagicMock(return_value=is_closing)
    mock_session.transport = MagicMock()
    mock_session.transport._framer = MagicMock()
    mock_session.transport._framer.max_size = 0

    # Mock the send_request method to handle server.version call with proper response
    def mock_send_request(method, params):
        if method == "server.version":
            return server_version_response
        return {"result": "success"}

    mock_session.send_request = AsyncMock(side_effect=mock_send_request)

    return mock_session


def create_mock_connect_rs(mock_session):
    """
    Create a mock connect_rs function that returns an async context manager.
    
    Args:
        mock_session (AsyncMock): The mock session to return
        
    Returns:
        AsyncMock: Mock connect_rs function
    """
    mock_connect_rs = AsyncMock()
    mock_connect_rs.__aenter__ = AsyncMock(return_value=mock_session)
    mock_connect_rs.__aexit__ = AsyncMock(return_value=None)
    return mock_connect_rs


def mock_connect_rs_with_session(mock_session):
    """
    Create a context manager for mocking aiorpcx.connect_rs.
    
    Args:
        mock_session (AsyncMock): The mock session to return
        
    Returns:
        ContextManager: Patched connect_rs with the mock session
    """
    mock_connect_rs = create_mock_connect_rs(mock_session)
    return patch(AIORPCX_CONNECT_RS_PATCH, return_value=mock_connect_rs)


def create_mock_batch(results=None):
    """
    Create a properly configured mock batch that matches aiorpcx interface.
    
    Args:
        results (list): Results to return from the batch
        
    Returns:
        AsyncMock: Configured mock batch
    """
    if results is None:
        results = [{"result": "success1"}, {"result": "success2"}]

    mock_batch = AsyncMock()
    mock_batch.__aenter__ = AsyncMock(return_value=mock_batch)
    mock_batch.__aexit__ = AsyncMock(return_value=None)
    mock_batch.add_request = MagicMock()
    mock_batch.results = results

    return mock_batch
