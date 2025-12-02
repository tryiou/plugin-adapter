#!/usr/bin/env python3
"""
Unit tests for Response Factory.
Tests cover basic response creation and serialization.
"""

import decimal
import json

from src.core.errors import NetworkError
from src.core.response_factory import ResponseFactory


class TestResponseFactory:
    """Test suite for ResponseFactory class."""

    def test_success_response_basic(self):
        """Test basic success response creation."""
        result = {"key": "value"}
        response = ResponseFactory.success(result)

        assert response['result'] == result
        assert response['error'] is None

    def test_success_response_none(self):
        """Test success response with None result."""
        response = ResponseFactory.success()

        assert response['result'] is None
        assert response['error'] is None

    def test_error_response_basic(self):
        """Test basic error response creation."""
        message = "Test error message"
        response = ResponseFactory.error(message)

        assert response['result'] is None
        assert response['error'] is not None
        assert response['error']['message'] == message
        assert response['error']['code'] == -1
        assert response['error']['type'] == "Error"

    def test_error_response_with_code(self):
        """Test error response with custom error code."""
        message = "Test error"
        code = -100
        response = ResponseFactory.error(message, code)

        assert response['result'] is None
        assert response['error']['message'] == message
        assert response['error']['code'] == code
        assert response['error']['type'] == "Error"

    def test_block_heights_response(self):
        """Test block heights response creation."""
        heights = {"BTC": 1000, "LTC": 950}
        response = ResponseFactory.block_heights(heights)

        assert response['result'] == heights
        assert response['error'] is None

    def test_utxos_response(self):
        """Test UTXOs response creation."""
        utxos = [{'address': 'test', 'value': 100}]
        response = ResponseFactory.utxos(utxos)

        assert response['result'] == {"utxos": utxos}
        assert response['error'] is None

    def test_balance_response(self):
        """Test balance response creation."""
        balance_data = {"confirmed": 100000000}
        response = ResponseFactory.balance(balance_data)

        assert response['result'] == balance_data
        assert response['error'] is None

    def test_transaction_response(self):
        """Test transaction response creation."""
        tx_data = {'txid': 'tx123', 'value': 0.1}
        response = ResponseFactory.transaction(tx_data)

        assert response['result'] == tx_data
        assert response['error'] is None

    def test_ping_response(self):
        """Test ping response creation."""
        response = ResponseFactory.ping()

        assert response['result'] == 1
        assert response['error'] is None

    def test_to_json_basic(self):
        """Test basic JSON serialization."""
        response = {'result': 'test', 'error': None}
        json_str = ResponseFactory.to_json(response)

        parsed = json.loads(json_str)
        assert parsed == response

    def test_to_json_with_simplejson(self):
        """Test JSON serialization with simplejson for decimal handling."""
        response = {'result': {'fee': decimal.Decimal('0.001')}, 'error': None}
        json_str = ResponseFactory.to_json(response, use_simplejson=True)

        parsed = json.loads(json_str)
        assert parsed['result']['fee'] == 0.001

    def test_create_success_response(self):
        """Test convenience method for success response."""
        result = {"test": "data"}
        json_str = ResponseFactory.create_success_response(result)

        parsed = json.loads(json_str)
        assert parsed['result'] == result
        assert parsed['error'] is None

    def test_create_error_response(self):
        """Test convenience method for error response."""
        message = "Test error"
        json_str = ResponseFactory.create_error_response(message, code=-100)

        parsed = json.loads(json_str)
        assert parsed['result'] is None
        assert parsed['error']['message'] == message
        assert parsed['error']['code'] == -100

    def test_create_utxos_response(self):
        """Test convenience method for UTXOs response."""
        utxos = [{'address': 'test', 'value': 100}]
        json_str = ResponseFactory.create_utxos_response(utxos)

        parsed = json.loads(json_str)
        assert parsed['result'] == {"utxos": utxos}
        assert parsed['error'] is None

    def test_create_error_from_exception(self):
        """Test convenience method for error response from exception."""
        error = NetworkError("Connection failed")
        json_str = ResponseFactory.create_error_from_exception(error)

        parsed = json.loads(json_str)
        assert parsed['result'] is None
        assert parsed['error']['message'] == "Connection failed"
        assert parsed['error']['code'] == -1
        assert parsed['error']['type'] == "NetworkError"

    def test_error_from_plugin_adapter_error(self):
        """Test error response from PluginAdapterError."""
        from src.core.errors import TransactionError
        error = TransactionError("Transaction failed")
        response = ResponseFactory.error_from_plugin_adapter_error(error)

        assert response['result'] is None
        assert response['error']['message'] == "Transaction failed"
        assert response['error']['code'] == -25
        assert response['error']['type'] == "TransactionError"
