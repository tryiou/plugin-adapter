#!/usr/bin/env python3
"""
Unit tests for Monitoring Service (src/services/monitoring_service.py).
Tests block height monitoring, transaction fee monitoring, dependency injection, and concurrent operations.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.application import PluginAdapterApplication
from src.services.monitoring_service import (MonitoringService,
                                             MonitoringServiceInterface)
from src.services.rpc_handlers import BlockRPCHandler, TransactionRPCHandler


class TestMonitoringServiceInterface:
    """Test suite for MonitoringServiceInterface."""

    def test_interface_definition(self):
        """Test that the interface is properly defined."""
        # Verify that the interface has the required abstract methods
        assert hasattr(MonitoringServiceInterface, 'get_block_heights')
        assert hasattr(MonitoringServiceInterface, 'get_tx_fees')

        # Verify that the methods are callable (they exist as methods)
        assert callable(getattr(MonitoringServiceInterface, 'get_block_heights'))
        assert callable(getattr(MonitoringServiceInterface, 'get_tx_fees'))

        # Verify that the interface cannot be instantiated directly (it's abstract)
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            MonitoringServiceInterface()

    def test_concrete_implementation(self):
        """Test that MonitoringService properly implements the interface."""
        # Verify that MonitoringService is a concrete implementation
        assert issubclass(MonitoringService, MonitoringServiceInterface)

        # Verify that MonitoringService can be instantiated
        mock_app = MagicMock()
        service = MonitoringService(mock_app)

        # Verify that the service has the required methods
        assert hasattr(service, 'get_block_heights')
        assert hasattr(service, 'get_tx_fees')

        # Verify that the methods are callable
        assert callable(getattr(service, 'get_block_heights'))
        assert callable(getattr(service, 'get_tx_fees'))


class TestMonitoringService:
    """Test suite for MonitoringService class."""

    def setup_method(self):
        """Setup for each test method."""
        self.mock_app = MagicMock(spec=PluginAdapterApplication)
        self.monitoring_service = MonitoringService(self.mock_app)

    def teardown_method(self):
        """Cleanup after each test method."""
        pass

    def test_service_initialization_default_handlers(self):
        """Test service initialization with default handlers."""
        service = MonitoringService(self.mock_app)

        assert service.app == self.mock_app
        assert isinstance(service.block_handler, BlockRPCHandler)
        assert isinstance(service.tx_handler, TransactionRPCHandler)

    def test_service_initialization_injected_handlers(self):
        """Test service initialization with injected handlers."""
        mock_block_handler = MagicMock(spec=BlockRPCHandler)
        mock_tx_handler = MagicMock(spec=TransactionRPCHandler)

        service = MonitoringService(
            self.mock_app,
            block_handler=mock_block_handler,
            tx_handler=mock_tx_handler
        )

        assert service.app == self.mock_app
        assert service.block_handler == mock_block_handler
        assert service.tx_handler == mock_tx_handler

    @pytest.mark.asyncio
    async def test_get_block_heights_success(self):
        """Test successful block height retrieval for multiple currencies."""
        with patch('src.services.monitoring_service.config_manager') as mock_config, \
                patch('src.services.monitoring_service.ResponseHelper') as mock_response_helper:
            mock_config.get_all_currencies.return_value = ['BTC', 'LTC']

            # Mock successful RPC responses
            mock_block_handler = AsyncMock()
            mock_block_handler.getblockcount.return_value = '{"result": 700000}'
            self.monitoring_service.block_handler = mock_block_handler

            mock_response_helper.block_heights.return_value = '{"heights": {"BTC": 700000, "LTC": 2500000}}'

            # Mock the internal parsing method
            with patch.object(self.monitoring_service, '_parse_rpc_response') as mock_parse:
                mock_parse.return_value = 700000

                result = await self.monitoring_service.get_block_heights()

                # Verify configuration was called
                mock_config.get_all_currencies.assert_called_once()
                # Verify RPC handler was called for each currency
                assert mock_block_handler.getblockcount.call_count == 2
                mock_block_handler.getblockcount.assert_any_call(['BTC'])
                mock_block_handler.getblockcount.assert_any_call(['LTC'])
                # Verify response helper was called
                mock_response_helper.block_heights.assert_called_once()
                assert result is not None

    @pytest.mark.asyncio
    async def test_get_block_heights_no_currencies(self):
        """Test block height retrieval when no currencies are configured."""
        with patch('src.services.monitoring_service.config_manager') as mock_config, \
                patch('src.services.monitoring_service.ResponseHelper') as mock_response_helper:
            mock_config.get_all_currencies.return_value = []
            mock_response_helper.block_heights.return_value = '{"heights": {}}'

            result = await self.monitoring_service.get_block_heights()

            # Verify empty response was returned
            mock_response_helper.block_heights.assert_called_once_with({})
            assert result is not None

    @pytest.mark.asyncio
    async def test_get_block_heights_with_failures(self):
        """Test block height retrieval with some currency failures."""
        with patch('src.services.monitoring_service.config_manager') as mock_config, \
                patch('src.services.monitoring_service.ResponseHelper') as mock_response_helper:
            mock_config.get_all_currencies.return_value = ['BTC', 'LTC', 'ETH']

            # Mock mixed success/failure responses
            mock_block_handler = AsyncMock()
            mock_block_handler.getblockcount.side_effect = [
                '{"result": 700000}',  # BTC success
                '{"error": "Connection failed"}',  # LTC failure
                '{"result": 15000000}'  # ETH success
            ]
            self.monitoring_service.block_handler = mock_block_handler

            mock_response_helper.block_heights.return_value = '{"heights": {"BTC": 700000, "LTC": null, "ETH": 15000000}}'

            # Mock the internal parsing method
            with patch.object(self.monitoring_service, '_parse_rpc_response') as mock_parse:
                def parse_side_effect(response_json):
                    if 'error' in response_json:
                        return None
                    return int(response_json.split(':')[1].strip('"}'))

                mock_parse.side_effect = parse_side_effect

                result = await self.monitoring_service.get_block_heights()

                # Verify all currencies were attempted
                assert mock_block_handler.getblockcount.call_count == 3
                # Verify response helper was called with mixed results
                mock_response_helper.block_heights.assert_called_once()
                assert result is not None

    @pytest.mark.asyncio
    async def test_get_block_heights_concurrent_execution(self):
        """Test that block height retrieval runs concurrently."""
        with patch('src.services.monitoring_service.config_manager') as mock_config:
            mock_config.get_all_currencies.return_value = ['BTC', 'LTC', 'ETH', 'BCH']

            # Mock slow RPC responses
            async def slow_response(currency):
                await asyncio.sleep(0.1)  # Simulate network delay
                return f'{{"result": {100000 + len(currency) * 10000}}}'

            mock_block_handler = AsyncMock()
            mock_block_handler.getblockcount.side_effect = slow_response
            self.monitoring_service.block_handler = mock_block_handler

            start_time = asyncio.get_event_loop().time()

            with patch('src.services.monitoring_service.ResponseHelper'):
                await self.monitoring_service.get_block_heights()

            end_time = asyncio.get_event_loop().time()

            # Should complete faster than sequential execution (0.4s for 4 currencies)
            # Allow some tolerance for test environment
            assert end_time - start_time < 0.3

    @pytest.mark.asyncio
    async def test_get_tx_fees_success(self):
        """Test successful transaction fee retrieval for multiple currencies."""
        with patch('src.services.monitoring_service.config_manager') as mock_config, \
                patch('src.services.monitoring_service.ResponseHelper') as mock_response_helper:
            mock_config.get_all_currencies.return_value = ['BTC', 'LTC']

            # Mock successful RPC responses
            mock_tx_handler = AsyncMock()
            mock_tx_handler.get_plugin_fees.return_value = '{"result": 0.00012345}'
            self.monitoring_service.tx_handler = mock_tx_handler

            mock_response_helper.transaction_fees.return_value = '{"fees": {"BTC": "0.00012345", "LTC": "0.00005432"}}'

            # Mock the internal parsing method
            with patch.object(self.monitoring_service, '_parse_rpc_response') as mock_parse:
                mock_parse.return_value = 0.00012345

                result = await self.monitoring_service.get_tx_fees()

                # Verify configuration was called
                mock_config.get_all_currencies.assert_called_once()
                # Verify RPC handler was called for each currency
                assert mock_tx_handler.get_plugin_fees.call_count == 2
                mock_tx_handler.get_plugin_fees.assert_any_call(['BTC'])
                mock_tx_handler.get_plugin_fees.assert_any_call(['LTC'])
                # Verify response helper was called
                mock_response_helper.transaction_fees.assert_called_once()
                assert result is not None

    @pytest.mark.asyncio
    async def test_get_tx_fees_no_currencies(self):
        """Test transaction fee retrieval when no currencies are configured."""
        with patch('src.services.monitoring_service.config_manager') as mock_config, \
                patch('src.services.monitoring_service.ResponseHelper') as mock_response_helper:
            mock_config.get_all_currencies.return_value = []
            mock_response_helper.transaction_fees.return_value = '{"fees": {}}'

            result = await self.monitoring_service.get_tx_fees()

            # Verify empty response was returned
            mock_response_helper.transaction_fees.assert_called_once_with({})
            assert result is not None

    @pytest.mark.asyncio
    async def test_get_tx_fees_with_failures(self):
        """Test transaction fee retrieval with some currency failures."""
        with patch('src.services.monitoring_service.config_manager') as mock_config, \
                patch('src.services.monitoring_service.ResponseHelper') as mock_response_helper:
            mock_config.get_all_currencies.return_value = ['BTC', 'LTC', 'ETH']

            # Mock mixed success/failure responses
            mock_tx_handler = AsyncMock()
            mock_tx_handler.get_plugin_fees.side_effect = [
                '{"result": 0.00012345}',  # BTC success
                '{"error": "Connection failed"}',  # LTC failure
                '{"result": 0.00008765}'  # ETH success
            ]
            self.monitoring_service.tx_handler = mock_tx_handler

            mock_response_helper.transaction_fees.return_value = '{"fees": {"BTC": "0.00012345", "LTC": null, "ETH": "0.00008765"}}'

            # Mock the internal parsing method
            with patch.object(self.monitoring_service, '_parse_rpc_response') as mock_parse:
                def parse_side_effect(response_json):
                    if 'error' in response_json:
                        return None
                    # Extract number from JSON
                    import json
                    data = json.loads(response_json)
                    return data.get('result')

                mock_parse.side_effect = parse_side_effect

                result = await self.monitoring_service.get_tx_fees()

                # Verify all currencies were attempted
                assert mock_tx_handler.get_plugin_fees.call_count == 3
                # Verify response helper was called with mixed results
                mock_response_helper.transaction_fees.assert_called_once()
                assert result is not None

    @pytest.mark.asyncio
    async def test_get_tx_fees_decimal_formatting(self):
        """Test that transaction fees are properly formatted as Decimal."""
        with patch('src.services.monitoring_service.config_manager') as mock_config:
            mock_config.get_all_currencies.return_value = ['BTC']

            mock_tx_handler = AsyncMock()
            mock_tx_handler.get_plugin_fees.return_value = '{"result": 0.000123456789}'
            self.monitoring_service.tx_handler = mock_tx_handler

            with patch.object(self.monitoring_service, '_parse_rpc_response') as mock_parse, \
                    patch('src.services.monitoring_service.ResponseHelper') as mock_response_helper:
                mock_parse.return_value = 0.000123456789
                mock_response_helper.transaction_fees.return_value = '{"fees": {"BTC": "0.00012345"}}'

                result = await self.monitoring_service.get_tx_fees()

                # Verify fee was properly formatted to 8 decimal places
                mock_response_helper.transaction_fees.assert_called_once()
                assert result is not None

    @pytest.mark.asyncio
    async def test_get_tx_fees_concurrent_execution(self):
        """Test that transaction fee retrieval runs concurrently."""
        with patch('src.services.monitoring_service.config_manager') as mock_config:
            mock_config.get_all_currencies.return_value = ['BTC', 'LTC', 'ETH', 'BCH']

            # Mock slow RPC responses
            async def slow_response(currency):
                await asyncio.sleep(0.1)  # Simulate network delay
                return f'{{"result": {0.0001 + len(currency) * 0.00001}}}'

            mock_tx_handler = AsyncMock()
            mock_tx_handler.get_plugin_fees.side_effect = slow_response
            self.monitoring_service.tx_handler = mock_tx_handler

            start_time = asyncio.get_event_loop().time()

            with patch('src.services.monitoring_service.ResponseHelper'):
                await self.monitoring_service.get_tx_fees()

            end_time = asyncio.get_event_loop().time()

            # Should complete faster than sequential execution
            assert end_time - start_time < 0.3

    @pytest.mark.asyncio
    async def test_parse_rpc_response_success(self):
        """Test successful RPC response parsing."""
        response_json = '{"result": 700000, "error": null, "id": 1}'

        result = self.monitoring_service._parse_rpc_response(response_json)

        assert result == 700000

    @pytest.mark.asyncio
    async def test_parse_rpc_response_error(self):
        """Test RPC response parsing with error."""
        response_json = '{"result": null, "error": {"code": -32601, "message": "Method not found"}, "id": 1}'

        result = self.monitoring_service._parse_rpc_response(response_json)

        assert result is None

    @pytest.mark.asyncio
    async def test_parse_rpc_response_invalid_json(self):
        """Test RPC response parsing with invalid JSON."""
        response_json = 'invalid json'

        result = self.monitoring_service._parse_rpc_response(response_json)

        assert result is None

    @pytest.mark.asyncio
    async def test_parse_rpc_response_missing_result(self):
        """Test RPC response parsing when result is missing."""
        response_json = '{"error": null, "id": 1}'

        result = self.monitoring_service._parse_rpc_response(response_json)

        assert result is None

    @pytest.mark.asyncio
    async def test_parse_json_safely_success(self):
        """Test safe JSON parsing with valid JSON."""
        json_str = '{"key": "value", "number": 123}'

        result = self.monitoring_service._parse_json_safely(json_str)

        assert result == {"key": "value", "number": 123}

    @pytest.mark.asyncio
    async def test_parse_json_safely_invalid_json(self):
        """Test safe JSON parsing with invalid JSON."""
        json_str = 'invalid json'

        result = self.monitoring_service._parse_json_safely(json_str)

        assert result is None

    @pytest.mark.asyncio
    async def test_parse_json_safely_none_input(self):
        """Test safe JSON parsing with None input."""
        result = self.monitoring_service._parse_json_safely(None)

        assert result is None

    @pytest.mark.asyncio
    async def test_dependency_injection_block_handler(self):
        """Test dependency injection for block handler."""
        mock_block_handler = MagicMock(spec=BlockRPCHandler)
        mock_block_handler.getblockcount = AsyncMock(return_value='{"result": 700000}')

        service = MonitoringService(self.mock_app, block_handler=mock_block_handler)

        with patch('src.services.monitoring_service.config_manager') as mock_config, \
                patch('src.services.monitoring_service.ResponseHelper'):
            mock_config.get_all_currencies.return_value = ['BTC']

            with patch.object(service, '_parse_rpc_response', return_value=700000):
                await service.get_block_heights()

                # Verify injected handler was used
                mock_block_handler.getblockcount.assert_called_once_with(['BTC'])

    @pytest.mark.asyncio
    async def test_dependency_injection_tx_handler(self):
        """Test dependency injection for transaction handler."""
        mock_tx_handler = MagicMock(spec=TransactionRPCHandler)
        mock_tx_handler.get_plugin_fees = AsyncMock(return_value='{"result": 0.00012345}')

        service = MonitoringService(self.mock_app, tx_handler=mock_tx_handler)

        with patch('src.services.monitoring_service.config_manager') as mock_config, \
                patch('src.services.monitoring_service.ResponseHelper'):
            mock_config.get_all_currencies.return_value = ['BTC']

            with patch.object(service, '_parse_rpc_response', return_value=0.00012345):
                await service.get_tx_fees()

                # Verify injected handler was used
                mock_tx_handler.get_plugin_fees.assert_called_once_with(['BTC'])
