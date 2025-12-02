#!/usr/bin/env python3
"""
Unit tests for Error Handling System.
Tests cover exception hierarchy and basic error handling.
"""

from src.core.error_handling import ErrorHandler
from src.core.errors import NetworkError, PluginAdapterError, ProtocolError


class TestPluginAdapterError:
    """Test suite for PluginAdapterError base class."""

    def test_plugin_adapter_error_creation(self):
        """Test basic PluginAdapterError creation."""
        error = PluginAdapterError("Test message")

        assert error.message == "Test message"
        assert error.error_code == -1
        assert str(error) == "Test message"

    def test_plugin_adapter_error_with_code(self):
        """Test PluginAdapterError with custom error code."""
        error = PluginAdapterError("Test message", error_code=-100)

        assert error.message == "Test message"
        assert error.error_code == -100


class TestNetworkError:
    """Test suite for NetworkError class."""

    def test_network_error_creation(self):
        """Test basic NetworkError creation."""
        error = NetworkError("Connection failed")

        assert error.message == "Connection failed"
        assert error.error_code == -1

    def test_network_error_inheritance(self):
        """Test NetworkError inheritance hierarchy."""
        error = NetworkError("Test message")

        assert isinstance(error, PluginAdapterError)
        assert isinstance(error, Exception)


class TestProtocolError:
    """Test suite for ProtocolError class."""

    def test_protocol_error_creation(self):
        """Test basic ProtocolError creation."""
        error = ProtocolError("Invalid protocol version")

        assert error.message == "Invalid protocol version"
        assert error.error_code == -2

    def test_protocol_error_inheritance(self):
        """Test ProtocolError inheritance hierarchy."""
        error = ProtocolError("Test message")

        assert isinstance(error, PluginAdapterError)
        assert isinstance(error, Exception)


class TestErrorHandler:
    """Test suite for ErrorHandler service class."""

    def test_handle_error_network_error(self):
        """Test handling NetworkError."""
        error = NetworkError("Connection failed")

        response = ErrorHandler.handle_error(error)

        assert response['result'] is None
        assert response['error'] is not None
        assert response['error']['code'] == -1
        assert response['error']['message'] == "Connection failed"
        assert response['error']['type'] == "NetworkError"

    def test_handle_error_protocol_error(self):
        """Test handling ProtocolError."""
        error = ProtocolError("Invalid protocol")

        response = ErrorHandler.handle_error(error)

        assert response['result'] is None
        assert response['error'] is not None
        assert response['error']['code'] == -2
        assert response['error']['message'] == "Invalid protocol"
        assert response['error']['type'] == "ProtocolError"

    def test_handle_unexpected_error(self):
        """Test handling unexpected errors."""
        original_error = ValueError("Unexpected error")

        response = ErrorHandler.handle_unexpected_error(original_error)

        assert response['result'] is None
        assert response['error'] is not None
        assert response['error']['code'] == -2
        assert "Unexpected error: Unexpected error" in response['error']['message']
        assert response['error']['type'] == "ProtocolError"

    def test_rpc_method_exceptions_decorator_success(self):
        """Test RPC method decorator with successful execution."""

        @ErrorHandler.handle_rpc_method_exceptions
        def successful_function():
            return {"result": "success"}

        result = successful_function()
        assert result == {"result": "success"}

    def test_rpc_method_exceptions_decorator_network_error(self):
        """Test RPC method decorator with NetworkError."""

        @ErrorHandler.handle_rpc_method_exceptions
        def network_error_function():
            raise NetworkError("Connection failed")

        result = network_error_function()
        assert result['result'] is None
        assert result['error']['type'] == "NetworkError"
        assert result['error']['message'] == "Connection failed"

    def test_rpc_method_exceptions_decorator_unexpected_error(self):
        """Test RPC method decorator with unexpected error."""

        @ErrorHandler.handle_rpc_method_exceptions
        def unexpected_error_function():
            raise ValueError("Unexpected error")

        result = unexpected_error_function()
        assert result['result'] is None
        assert result['error']['type'] == "ProtocolError"
        assert "Unexpected error: Unexpected error" in result['error']['message']
