#!/usr/bin/env python3
"""
Unit tests for Utilities.
Tests cover logging functionality and response helper methods.
"""

import logging
import time
from io import StringIO

from src.core.errors import NetworkError
from src.utils.operation_logger import OperationLogger
from src.utils.response_helper import ResponseHelper


class TestOperationLogger:
    """Test suite for OperationLogger class."""

    def setup_method(self):
        """Setup for each test method."""
        # Create a string buffer to capture log output
        self.log_capture = StringIO()
        self.handler = logging.StreamHandler(self.log_capture)

        # Get the logger and add our handler
        logger = logging.getLogger('src.utils.operation_logger')
        logger.addHandler(self.handler)
        logger.setLevel(logging.INFO)

        self.logger = logger

    def teardown_method(self):
        """Cleanup after each test method."""
        self.logger.removeHandler(self.handler)
        self.log_capture.close()

    def test_start_operation(self):
        """Test starting an operation."""
        start_time = OperationLogger.start("test_operation", "test_context")

        # Check that log was written
        log_output = self.log_capture.getvalue()
        assert "[test_context] Sending test_operation" in log_output

        # Check that start_time is a reasonable timestamp
        current_time = int(time.time() * 1000)
        assert abs(current_time - start_time) < 1000  # Within 1 second

    def test_end_operation_short_duration(self):
        """Test ending an operation with short duration."""
        start_time = int(time.time() * 1000) - 500  # 500ms ago

        OperationLogger.end("test_operation", start_time, "test_context")

        log_output = self.log_capture.getvalue()
        assert "[test_context] test_operation completed in 500ms" in log_output

    def test_end_operation_long_duration(self):
        """Test ending an operation with long duration."""
        start_time = int(time.time() * 1000) - 2000  # 2 seconds ago

        OperationLogger.end("test_operation", start_time, "test_context")

        log_output = self.log_capture.getvalue()
        assert "[test_context] test_operation completed in 2.000s" in log_output

    def test_error_operation(self):
        """Test logging an error operation."""
        test_error = ValueError("Test error message")

        OperationLogger.error("test_operation", "test_context", test_error)

        log_output = self.log_capture.getvalue()
        assert "[test_context] test_operation failed: Test error message" in log_output


class TestResponseHelper:
    """Test suite for ResponseHelper class."""

    def test_success_response(self):
        """Test success response creation."""
        result = {"key": "value"}
        response = ResponseHelper.success(result)

        import json
        parsed = json.loads(response)
        assert parsed['result'] == result
        assert parsed['error'] is None

    def test_error_response(self):
        """Test error response creation."""
        message = "Test error"
        response = ResponseHelper.error(message)

        import json
        parsed = json.loads(response)
        assert parsed['result'] is None
        assert parsed['error']['message'] == message
        assert parsed['error']['code'] == -1
        assert parsed['error']['type'] == "Error"

    def test_block_heights_response(self):
        """Test block heights response."""
        heights = {"BTC": 1000, "LTC": 950}
        response = ResponseHelper.block_heights(heights)

        import json
        parsed = json.loads(response)
        assert parsed['result'] == heights
        assert parsed['error'] is None

    def test_utxos_response(self):
        """Test UTXOs response."""
        utxos = [{"address": "test", "value": 100}]
        response = ResponseHelper.utxos(utxos)

        import json
        parsed = json.loads(response)
        assert parsed['result'] == {"utxos": utxos}
        assert parsed['error'] is None

    def test_transaction_response(self):
        """Test transaction response."""
        tx_data = {"txid": "tx123", "value": 0.1}
        response = ResponseHelper.transaction(tx_data)

        import json
        parsed = json.loads(response)
        assert parsed['result'] == tx_data
        assert parsed['error'] is None

    def test_ping_response(self):
        """Test ping response."""
        response = ResponseHelper.ping()

        import json
        parsed = json.loads(response)
        assert parsed['result'] == 1
        assert parsed['error'] is None

    def test_from_exception_network_error(self):
        """Test response creation from NetworkError."""
        error = NetworkError("Connection failed")
        response = ResponseHelper.from_exception(error)

        import json
        parsed = json.loads(response)
        assert parsed['result'] is None
        assert parsed['error']['message'] == "Connection failed"
        assert parsed['error']['code'] == -1
        assert parsed['error']['type'] == "NetworkError"

    def test_validation_error_convenience(self):
        """Test validation error convenience method."""
        message = "Invalid parameter"
        response = ResponseHelper.validation_error(message)

        import json
        parsed = json.loads(response)
        assert parsed['result'] is None
        assert parsed['error']['message'] == message
        assert parsed['error']['code'] == -32602
        assert parsed['error']['type'] == "ValidationError"

    def test_network_error_convenience(self):
        """Test network error convenience method."""
        message = "Connection timeout"
        response = ResponseHelper.network_error(message)

        import json
        parsed = json.loads(response)
        assert parsed['result'] is None
        assert parsed['error']['message'] == message
        assert parsed['error']['code'] == -32603
        assert parsed['error']['type'] == "NetworkError"
