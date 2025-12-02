#!/usr/bin/env python3
"""
Unit tests for RPC handlers module.
Tests cover basic RPC handler functionality.
"""

import datetime
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.errors import NetworkError, ValidationError
from src.services.rpc_handlers import (BalanceRPCHandler, BaseRPCHandler,
                                       BlockRPCHandler, HistoryRPCHandler,
                                       TimestampMillisec64,
                                       TransactionRPCHandler,
                                       UtilityRPCHandler, UTXORPCHandler,
                                       parse_response, validate_rpc_params)


class TestUtilityFunctions:
    """Test suite for utility functions."""

    def test_validate_rpc_params_valid(self):
        """Test valid RPC parameters."""
        result = validate_rpc_params(["BTC", "param1"])
        assert result is None

    def test_validate_rpc_params_invalid_length(self):
        """Test RPC parameters with invalid length."""
        result = validate_rpc_params([])
        assert isinstance(result, ValidationError)
        assert "Invalid parameters" in result.message

    def test_validate_rpc_params_invalid_type(self):
        """Test RPC parameters with invalid type."""
        result = validate_rpc_params("invalid")
        assert isinstance(result, ValidationError)
        assert "Invalid parameters" in result.message

    def test_validate_rpc_params_invalid_currency(self):
        """Test RPC parameters with invalid currency."""
        result = validate_rpc_params([None, "param1"])
        assert isinstance(result, ValidationError)
        assert "Invalid currency parameter" in result.message

    def test_validate_rpc_params_min_length(self):
        """Test RPC parameters with custom minimum length."""
        result = validate_rpc_params(["BTC"], min_length=2)
        assert isinstance(result, ValidationError)
        assert "Invalid parameters" in result.message

    def test_parse_response_success(self):
        """Test successful response parsing."""
        raw_response = [[
            {
                "address": "address1",
                "tx_hash": "tx123",
                "tx_pos": 0,
                "height": 1000,
                "value": 100000000
            }
        ]]
        result = parse_response(raw_response)
        assert result is not None
        assert len(result) == 1
        assert result[0]["address"] == "address1"
        assert result[0]["txhash"] == "tx123"
        assert result[0]["vout"] == 0
        assert result[0]["block_number"] == 1000
        assert result[0]["value"] == 1.0

    def test_parse_response_empty(self):
        """Test parsing empty response."""
        result = parse_response([])
        assert result == []

    def test_parse_response_none(self):
        """Test parsing None response."""
        result = parse_response(None)
        assert result is None

    def test_parse_response_invalid_data(self):
        """Test parsing invalid response data."""
        # Missing required keys
        raw_response = [[{"invalid_key": "value"}]]
        result = parse_response(raw_response)
        assert result is None

    def test_parse_response_type_error(self):
        """Test parsing response with type errors."""
        # Invalid height value
        raw_response = [[{
            "address": "address1",
            "tx_hash": "tx123",
            "tx_pos": "invalid",
            "height": "invalid",
            "value": "invalid"
        }]]
        result = parse_response(raw_response)
        assert result is None

    def test_parse_response_key_error(self):
        """Test parsing response with missing keys."""
        raw_response = [[{"address": "address1"}]]
        result = parse_response(raw_response)
        assert result is None

    def test_timestamp_millisec64(self):
        """Test timestamp generation."""
        timestamp = TimestampMillisec64()
        assert isinstance(timestamp, int)
        assert timestamp > 0

        # Test that it's reasonably current (within last hour)
        current_time = datetime.datetime.utcnow()
        expected_min = int((current_time - datetime.datetime(1970, 1, 1)).total_seconds() * 1000) - 3600000
        assert timestamp >= expected_min


class TestBaseRPCHandler:
    """Test suite for BaseRPCHandler class."""

    def setup_method(self):
        """Setup for each test method."""
        self.mock_app = MagicMock()
        self.handler = BaseRPCHandler(self.mock_app)

    def test_validate_currency_valid(self):
        """Test valid currency validation."""
        with patch('src.services.rpc_handlers.config_manager') as mock_config:
            mock_config.has_currency.return_value = True
            # Should not raise any exception
            self.handler._validate_currency("BTC")

    def test_validate_currency_empty(self):
        """Test currency validation with empty currency."""
        with pytest.raises(ValidationError) as exc_info:
            self.handler._validate_currency("")
        assert "Currency parameter is required" in str(exc_info.value)

    def test_validate_currency_none(self):
        """Test currency validation with None currency."""
        with pytest.raises(ValidationError) as exc_info:
            self.handler._validate_currency(None)
        assert "Currency parameter is required" in str(exc_info.value)

    def test_validate_currency_invalid_type(self):
        """Test currency validation with invalid type."""
        with pytest.raises(ValidationError) as exc_info:
            self.handler._validate_currency(123)
        assert "Currency parameter is required" in str(exc_info.value)

    def test_validate_currency_unsupported(self):
        """Test currency validation with unsupported currency."""
        with patch('src.services.rpc_handlers.config_manager') as mock_config:
            mock_config.has_currency.return_value = False
            with pytest.raises(ValidationError) as exc_info:
                self.handler._validate_currency("INVALID")
            assert "Unsupported currency: INVALID" in str(exc_info.value)

    def test_parse_addresses_string(self):
        """Test address parsing from string."""
        addresses = self.handler._parse_addresses("addr1,addr2,addr3")
        assert addresses == ["addr1", "addr2", "addr3"]

    def test_parse_addresses_list(self):
        """Test address parsing from list."""
        addresses = self.handler._parse_addresses(["addr1", "addr2", "addr3"])
        assert addresses == ["addr1", "addr2", "addr3"]

    def test_parse_addresses_json_string(self):
        """Test address parsing from JSON string."""
        addresses = self.handler._parse_addresses('["addr1", "addr2", "addr3"]')
        assert addresses == ["addr1", "addr2", "addr3"]

    def test_parse_addresses_empty(self):
        """Test address parsing with empty input."""
        addresses = self.handler._parse_addresses("")
        assert addresses == []

    def test_parse_addresses_none(self):
        """Test address parsing with None input."""
        addresses = self.handler._parse_addresses(None)
        assert addresses == []

    def test_parse_addresses_invalid_json(self):
        """Test address parsing with invalid JSON."""
        addresses = self.handler._parse_addresses('invalid json')
        assert addresses == ["invalid json"]

    def test_parse_addresses_mixed(self):
        """Test address parsing with mixed valid/invalid addresses."""
        addresses = self.handler._parse_addresses(["addr1", "", "addr3", None])
        assert addresses == ["addr1", "addr3"]


class TestUTXORPCHandler:
    """Test suite for UTXORPCHandler class."""

    def setup_method(self):
        """Setup for each test method."""
        self.mock_app = MagicMock()
        self.handler = UTXORPCHandler(self.mock_app)

    @pytest.mark.asyncio
    async def test_getutxos_success(self):
        """Test successful UTXOs retrieval."""
        # Mock successful response - format expected by parse_response
        mock_response = [[
            {
                "address": "address1",
                "tx_hash": "tx123",
                "tx_pos": 0,
                "height": 1000,
                "value": 100000000
            }
        ]]
        mock_socket = AsyncMock()
        mock_socket.send_batch.return_value = mock_response

        # Mock the get_socket method to return the mock socket
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        result = await self.handler.getutxos(["BTC", ["address1"]])

        # Result should be a JSON string
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is not None
        assert parsed_result["error"] is None

    @pytest.mark.asyncio
    async def test_getutxos_error(self):
        """Test UTXOs retrieval with error."""
        from src.core.errors import NetworkError
        mock_socket = AsyncMock()
        mock_socket.send_batch.side_effect = NetworkError("Connection failed")
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        result = await self.handler.getutxos(["BTC", ["address1"]])

        # Result should be a JSON string with error
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is None
        assert parsed_result["error"] is not None
        assert parsed_result["error"]["type"] == "NetworkError"

    @pytest.mark.asyncio
    async def test_getutxos_empty_addresses(self):
        """Test UTXOs retrieval with empty addresses."""
        result = await self.handler.getutxos(["BTC", []])

        # Result should be a JSON string with empty UTXOs
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is None
        assert parsed_result["error"] is not None

    @pytest.mark.asyncio
    async def test_getutxos_invalid_addresses(self):
        """Test UTXOs retrieval with invalid addresses."""
        result = await self.handler.getutxos(["BTC", ""])

        # Result should be a JSON string with empty UTXOs
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is None
        assert parsed_result["error"] is not None

    @pytest.mark.asyncio
    async def test_getutxos_parse_response_failure(self):
        """Test UTXOs retrieval when parse_response fails."""
        # Mock response that will cause parse_response to fail
        mock_response = [[{"invalid_key": "value"}]]
        mock_socket = AsyncMock()
        mock_socket.send_batch.return_value = mock_response
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        result = await self.handler.getutxos(["BTC", ["address1"]])

        # Result should be a JSON string with empty UTXOs
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] == {"utxos": []}
        assert parsed_result["error"] is None

    @pytest.mark.asyncio
    async def test_getutxos_network_error(self):
        """Test UTXOs retrieval with network error."""
        mock_socket = AsyncMock()
        mock_socket.send_batch.side_effect = NetworkError("Network error")
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        result = await self.handler.getutxos(["BTC", ["address1"]])

        # Result should be a JSON string with error
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is None
        assert parsed_result["error"] is not None
        assert parsed_result["error"]["type"] == "NetworkError"


class TestTransactionRPCHandler:
    """Test suite for TransactionRPCHandler class."""

    def setup_method(self):
        """Setup for each test method."""
        self.mock_app = MagicMock()
        self.handler = TransactionRPCHandler(self.mock_app)

    @pytest.mark.asyncio
    async def test_gettransaction_success(self):
        """Test successful transaction retrieval."""
        mock_response = {"txid": "tx123", "value": 0.1}
        mock_socket = AsyncMock()
        mock_socket.send_message.return_value = mock_response
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        # Mock the currency validation to bypass it
        with patch.object(self.handler, '_validate_currency'):
            result = await self.handler.gettransaction(["BTC", "tx123"])

        # Result should be a JSON string
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is not None
        assert parsed_result["error"] is None

    @pytest.mark.asyncio
    async def test_gettransaction_invalid_params(self):
        """Test transaction retrieval with invalid parameters."""
        with patch.object(self.handler, '_validate_currency'):
            result = await self.handler.gettransaction(["BTC"])

        # Result should be a JSON string with error
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is None
        assert parsed_result["error"] is not None
        assert parsed_result["error"]["type"] == "IndexError"

    @pytest.mark.asyncio
    async def test_gettransaction_network_error(self):
        """Test transaction retrieval with network error."""
        mock_socket = AsyncMock()
        mock_socket.send_message.side_effect = NetworkError("Network error")
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        with patch.object(self.handler, '_validate_currency'):
            result = await self.handler.gettransaction(["BTC", "tx123"])

        # Result should be a JSON string with error
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is None
        assert parsed_result["error"] is not None
        assert parsed_result["error"]["type"] == "NetworkError"

    @pytest.mark.asyncio
    async def test_getrawtransaction_success(self):
        """Test successful raw transaction retrieval."""
        mock_response = {"txid": "tx123", "hex": "rawtx"}
        mock_socket = AsyncMock()
        mock_socket.send_message.return_value = mock_response
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        with patch.object(self.handler, '_validate_currency'):
            result = await self.handler.getrawtransaction(["BTC", "tx123"])

        # Result should be a JSON string
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is not None
        assert parsed_result["error"] is None

    @pytest.mark.asyncio
    async def test_getrawtransaction_with_verbose(self):
        """Test raw transaction retrieval with verbose flag."""
        mock_response = {"txid": "tx123", "hex": "rawtx", "verbose": True}
        mock_socket = AsyncMock()
        mock_socket.send_message.return_value = mock_response
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        with patch.object(self.handler, '_validate_currency'):
            result = await self.handler.getrawtransaction(["BTC", "tx123", True])

        # Result should be a JSON string
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is not None
        assert parsed_result["error"] is None

    @pytest.mark.asyncio
    async def test_getrawtransaction_invalid_currency(self):
        """Test raw transaction retrieval with invalid currency."""
        with patch.object(self.handler, '_validate_currency') as mock_validate:
            mock_validate.side_effect = ValidationError("Invalid currency")
            result = await self.handler.getrawtransaction(["INVALID", "tx123"])

        # Result should be a JSON string with error
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is None
        assert parsed_result["error"] is not None
        assert parsed_result["error"]["type"] == "ValidationError"

    @pytest.mark.asyncio
    async def test_getrawmempool_success(self):
        """Test successful mempool retrieval."""
        mock_response = ["tx1", "tx2", "tx3"]
        mock_socket = AsyncMock()
        mock_socket.send_message.return_value = mock_response
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        with patch.object(self.handler, '_validate_currency'):
            result = await self.handler.getrawmempool(["BTC"])

        # Result should be a JSON string
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is not None
        assert parsed_result["error"] is None

    @pytest.mark.asyncio
    async def test_getrawmempool_with_verbose(self):
        """Test mempool retrieval with verbose flag."""
        mock_response = {"tx1": {"size": 100}, "tx2": {"size": 200}}
        mock_socket = AsyncMock()
        mock_socket.send_message.return_value = mock_response
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        with patch.object(self.handler, '_validate_currency'):
            result = await self.handler.getrawmempool(["BTC", True])

        # Result should be a JSON string
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is not None
        assert parsed_result["error"] is None

    @pytest.mark.asyncio
    async def test_sendrawtransaction_success(self):
        """Test successful transaction sending."""
        mock_response = {"txid": "new_tx123"}
        mock_socket = AsyncMock()
        mock_socket.send_message.return_value = mock_response
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        with patch.object(self.handler, '_validate_currency'):
            result = await self.handler.sendrawtransaction(["BTC", "rawtx123"])

        # Result should be a JSON string
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is not None
        assert parsed_result["error"] is None

    @pytest.mark.asyncio
    async def test_sendrawtransaction_invalid_params(self):
        """Test transaction sending with invalid parameters."""
        with patch.object(self.handler, '_validate_currency'):
            result = await self.handler.sendrawtransaction(["BTC"])

        # Result should be a JSON string with error
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is None
        assert parsed_result["error"] is not None
        assert parsed_result["error"]["type"] == "IndexError"

    @pytest.mark.asyncio
    async def test_sendrawtransaction_network_error(self):
        """Test transaction sending with network error."""
        mock_socket = AsyncMock()
        mock_socket.send_message.side_effect = NetworkError("Network error")
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        with patch.object(self.handler, '_validate_currency'):
            result = await self.handler.sendrawtransaction(["BTC", "rawtx123"])

        # Result should be a JSON string with error
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is None
        assert parsed_result["error"] is not None
        assert parsed_result["error"]["type"] == "NetworkError"

    @pytest.mark.asyncio
    async def test_get_plugin_fees_success(self):
        """Test successful plugin fees retrieval."""
        mock_socket = AsyncMock()
        mock_socket.send_message.return_value = 0.0001
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        with patch.object(self.handler, '_validate_currency'):
            result = await self.handler.get_plugin_fees(["BTC"])

        # Result should be a JSON string
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] == 0.0001
        assert parsed_result["error"] is None

    @pytest.mark.asyncio
    async def test_get_plugin_fees_none_response(self):
        """Test plugin fees retrieval with None response."""
        mock_socket = AsyncMock()
        mock_socket.send_message.return_value = None
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        with patch.object(self.handler, '_validate_currency'):
            result = await self.handler.get_plugin_fees(["BTC"])

        # Result should be a JSON string with None value
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is None
        assert parsed_result["error"] is None

    @pytest.mark.asyncio
    async def test_get_plugin_fees_invalid_float(self):
        """Test plugin fees retrieval with invalid float response."""
        mock_socket = AsyncMock()
        mock_socket.send_message.return_value = "invalid"
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        with patch.object(self.handler, '_validate_currency'):
            result = await self.handler.get_plugin_fees(["BTC"])

        # Result should be a JSON string with None value
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is None
        assert parsed_result["error"] is None

    @pytest.mark.asyncio
    async def test_get_plugin_fees_network_error(self):
        """Test plugin fees retrieval with network error."""
        mock_socket = AsyncMock()
        mock_socket.send_message.side_effect = NetworkError("Network error")
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        with patch.object(self.handler, '_validate_currency'):
            result = await self.handler.get_plugin_fees(["BTC"])

        # Result should be a JSON string with error
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is None
        assert parsed_result["error"] is not None
        assert parsed_result["error"]["type"] == "NetworkError"


class TestBlockRPCHandler:
    """Test suite for BlockRPCHandler class."""

    def setup_method(self):
        """Setup for each test method."""
        self.mock_app = MagicMock()
        self.handler = BlockRPCHandler(self.mock_app)

    @pytest.mark.asyncio
    async def test_getblock_success(self):
        """Test successful block retrieval."""
        mock_response = {"hash": "block123", "height": 1000}
        mock_socket = AsyncMock()
        mock_socket.send_message.return_value = mock_response
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        with patch.object(self.handler, '_validate_currency'):
            result = await self.handler.getblock(["BTC", "block123"])

        # Result should be a JSON string
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is not None
        assert parsed_result["error"] is None

    @pytest.mark.asyncio
    async def test_getblock_with_verbose(self):
        """Test block retrieval with verbose flag."""
        mock_response = {"hash": "block123", "height": 1000, "verbose": True}
        mock_socket = AsyncMock()
        mock_socket.send_message.return_value = mock_response
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        with patch.object(self.handler, '_validate_currency'):
            result = await self.handler.getblock(["BTC", "block123", True])

        # Result should be a JSON string
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is not None
        assert parsed_result["error"] is None

    @pytest.mark.asyncio
    async def test_getblock_invalid_params(self):
        """Test block retrieval with invalid parameters."""
        with patch.object(self.handler, '_validate_currency'):
            result = await self.handler.getblock(["BTC"])

        # Result should be a JSON string with error
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is None
        assert parsed_result["error"] is not None
        assert parsed_result["error"]["type"] == "IndexError"

    @pytest.mark.asyncio
    async def test_getblock_network_error(self):
        """Test block retrieval with network error."""
        mock_socket = AsyncMock()
        mock_socket.send_message.side_effect = NetworkError("Network error")
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        with patch.object(self.handler, '_validate_currency'):
            result = await self.handler.getblock(["BTC", "block123"])

        # Result should be a JSON string with error
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is None
        assert parsed_result["error"] is not None
        assert parsed_result["error"]["type"] == "NetworkError"

    @pytest.mark.asyncio
    async def test_getblockcount_success(self):
        """Test successful block count retrieval."""
        mock_response = 1000
        mock_socket = AsyncMock()
        mock_socket.send_message.return_value = mock_response
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        with patch.object(self.handler, '_validate_currency'):
            result = await self.handler.getblockcount(["BTC"])

        # Result should be a JSON string
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is not None
        assert parsed_result["error"] is None

    @pytest.mark.asyncio
    async def test_getblockcount_network_error(self):
        """Test block count retrieval with network error."""
        mock_socket = AsyncMock()
        mock_socket.send_message.side_effect = NetworkError("Network error")
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        with patch.object(self.handler, '_validate_currency'):
            result = await self.handler.getblockcount(["BTC"])

        # Result should be a JSON string with error
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is None
        assert parsed_result["error"] is not None
        assert parsed_result["error"]["type"] == "NetworkError"

    @pytest.mark.asyncio
    async def test_getblockhash_success(self):
        """Test successful block hash retrieval."""
        mock_response = "block123"
        mock_socket = AsyncMock()
        mock_socket.send_message.return_value = mock_response
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        with patch.object(self.handler, '_validate_currency'):
            result = await self.handler.getblockhash(["BTC", 1000])

        # Result should be a JSON string
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is not None
        assert parsed_result["error"] is None

    @pytest.mark.asyncio
    async def test_getblockhash_invalid_params(self):
        """Test block hash retrieval with invalid parameters."""
        with patch.object(self.handler, '_validate_currency'):
            result = await self.handler.getblockhash(["BTC"])

        # Result should be a JSON string with error
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is None
        assert parsed_result["error"] is not None
        assert parsed_result["error"]["type"] == "IndexError"

    @pytest.mark.asyncio
    async def test_getblockhash_network_error(self):
        """Test block hash retrieval with network error."""
        mock_socket = AsyncMock()
        mock_socket.send_message.side_effect = NetworkError("Network error")
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        with patch.object(self.handler, '_validate_currency'):
            result = await self.handler.getblockhash(["BTC", 1000])

        # Result should be a JSON string with error
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is None
        assert parsed_result["error"] is not None
        assert parsed_result["error"]["type"] == "NetworkError"


class TestBalanceRPCHandler:
    """Test suite for BalanceRPCHandler class."""

    def setup_method(self):
        """Setup for each test method."""
        self.mock_app = MagicMock()
        self.handler = BalanceRPCHandler(self.mock_app)

    @pytest.mark.asyncio
    async def test_getbalance_success(self):
        """Test successful balance retrieval."""
        mock_response = {"confirmed": 100000000, "unconfirmed": 50000000}
        mock_socket = AsyncMock()
        mock_socket.send_message.return_value = mock_response
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        with patch.object(self.handler, '_validate_currency'):
            result = await self.handler.getbalance(["BTC", "address1"])

        # Result should be a JSON string
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is not None
        assert parsed_result["error"] is None
        # Check that values were converted to float
        assert parsed_result["result"]["confirmed"] == 1.0
        assert parsed_result["result"]["unconfirmed"] == 0.5

    @pytest.mark.asyncio
    async def test_getbalance_zero_values(self):
        """Test balance retrieval with zero values."""
        mock_response = {"confirmed": 0, "unconfirmed": 0}
        mock_socket = AsyncMock()
        mock_socket.send_message.return_value = mock_response
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        with patch.object(self.handler, '_validate_currency'):
            result = await self.handler.getbalance(["BTC", "address1"])

        # Result should be a JSON string
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is not None
        assert parsed_result["error"] is None
        # Check that zero values are preserved
        assert parsed_result["result"]["confirmed"] == 0
        assert parsed_result["result"]["unconfirmed"] == 0

    @pytest.mark.asyncio
    async def test_getbalance_invalid_params(self):
        """Test balance retrieval with invalid parameters."""
        with patch.object(self.handler, '_validate_currency'):
            result = await self.handler.getbalance(["BTC"])

        # Result should be a JSON string with error
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is None
        assert parsed_result["error"] is not None
        assert parsed_result["error"]["type"] == "IndexError"

    @pytest.mark.asyncio
    async def test_getbalance_network_error(self):
        """Test balance retrieval with network error."""
        mock_socket = AsyncMock()
        mock_socket.send_message.side_effect = NetworkError("Network error")
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        with patch.object(self.handler, '_validate_currency'):
            result = await self.handler.getbalance(["BTC", "address1"])

        # Result should be a JSON string with error
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is None
        assert parsed_result["error"] is not None
        assert parsed_result["error"]["type"] == "NetworkError"


class TestHistoryRPCHandler:
    """Test suite for HistoryRPCHandler class."""

    def setup_method(self):
        """Setup for each test method."""
        self.mock_app = MagicMock()
        self.handler = HistoryRPCHandler(self.mock_app)

    @pytest.mark.asyncio
    async def test_gethistory_success(self):
        """Test successful transaction history retrieval."""
        mock_response = [{"tx_hash": "tx123", "height": 1000}]
        mock_socket = AsyncMock()
        mock_socket.send_batch.return_value = mock_response
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        result = await self.handler.gethistory(["BTC", "address1"])

        # Result should be a JSON string
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is not None
        assert parsed_result["error"] is None

    @pytest.mark.asyncio
    async def test_gethistory_empty_response(self):
        """Test transaction history retrieval with empty response."""
        mock_socket = AsyncMock()
        mock_socket.send_batch.return_value = None
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        result = await self.handler.gethistory(["BTC", "address1"])

        # Result should be a JSON string with empty history
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] == []
        assert parsed_result["error"] is None

    @pytest.mark.asyncio
    async def test_gethistory_filtered_response(self):
        """Test transaction history retrieval with filtered response."""
        mock_response = [{"tx_hash": "tx123", "height": 1000}, {}, {"tx_hash": "tx456", "height": 2000}]
        mock_socket = AsyncMock()
        mock_socket.send_batch.return_value = mock_response
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        result = await self.handler.gethistory(["BTC", "address1"])

        # Result should be a JSON string with filtered history
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is not None
        assert parsed_result["error"] is None

    @pytest.mark.asyncio
    async def test_gethistory_network_error(self):
        """Test transaction history retrieval with network error."""
        mock_socket = AsyncMock()
        mock_socket.send_batch.side_effect = NetworkError("Network error")
        self.mock_app.connection_manager.get_socket = AsyncMock(return_value=mock_socket)

        result = await self.handler.gethistory(["BTC", "address1"])

        # Result should be a JSON string with error
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is None
        assert parsed_result["error"] is not None
        assert parsed_result["error"]["type"] == "NetworkError"


class TestUtilityRPCHandler:
    """Test suite for UtilityRPCHandler class."""

    def setup_method(self):
        """Setup for each test method."""
        self.handler = UtilityRPCHandler()

    @pytest.mark.asyncio
    async def test_ping(self):
        """Test ping functionality."""
        result = await self.handler.ping()

        # Result should be a JSON string
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert parsed_result["result"] is not None
        assert parsed_result["error"] is None
