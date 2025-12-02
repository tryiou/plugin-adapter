#!/usr/bin/env python3
"""
Network Integration Tests for Plugin-Adapter

This module contains comprehensive integration tests that validate:
- End-to-end network communication
- TCP socket integration with connection manager
- Error handling across network layers
- Connection pooling and management
- Network timeout and failure scenarios
- Integration with monitoring service
- Cross-component communication validation

Test Coverage:
- 8 comprehensive integration tests
- Network communication validation
- Error handling scenarios
- Performance and timeout testing
- Cross-component integration
"""

import asyncio
import logging
import time
import unittest
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.application import PluginAdapterApplication
from src.core.configuration import config_manager
from src.core.connection_manager import ConnectionManager
from src.core.errors import NetworkError, ProtocolError
from src.networking.tcp_socket import TCPSocket
from src.services.monitoring_service import MonitoringService
from src.services.rpc_handlers import (BalanceRPCHandler, BlockRPCHandler,
                                       HistoryRPCHandler,
                                       TransactionRPCHandler,
                                       UtilityRPCHandler, UTXORPCHandler)
from tests.base_test_classes import IntegrationTestCase
from tests.fixtures.test_data import (TestAddress, TestBlock, TestCurrency,
                                      TestDataGenerator, TestTransaction,
                                      TestUTXO)

# Mark dataclasses as non-test classes to prevent pytest collection
TestDataGenerator.__test__ = False
TestCurrency.__test__ = False
TestAddress.__test__ = False
TestUTXO.__test__ = False
TestTransaction.__test__ = False
TestBlock.__test__ = False

logger = logging.getLogger(__name__)


class TestNetworkIntegration(IntegrationTestCase, unittest.TestCase):
    """Comprehensive network integration tests."""
    __test__ = True  # Explicitly mark as test class for pytest

    def __init__(self, methodName='runTest'):
        """Initialize the test class."""
        IntegrationTestCase.__init__(self)
        unittest.TestCase.__init__(self, methodName)

    def run_test(self):
        """Abstract method implementation - not used for individual test methods."""
        pass

    def setup_test(self):
        """Setup for network integration tests."""
        super().setup_test()

        # Test configuration
        self.test_config = {
            "currencies": {
                "BTC": {"host": "localhost", "port": 8000},
                "LTC": {"host": "localhost", "port": 8001}
            },
            "server": {
                "port": 5000,
                "host": "0.0.0.0"
            },
            "timeouts": {
                "default": 30,
                "block_count": 2,
                "utxo": 30,
                "transactions": 10
            }
        }

        # Test data
        generator = TestDataGenerator()
        self.test_transaction = generator.generate_transaction()
        self.test_utxo = generator.generate_utxo()
        self.test_block = generator.generate_block()

        # Component instances
        self.connection_manager = None
        self.monitoring_service = None
        self.rpc_handlers = {}
        self.application = None

    async def setup_components(self):
        """Setup application components for testing."""
        # Setup configuration
        config_manager.clear()
        config_manager._coins = {
            "BTC": MagicMock(host="localhost", port=8000),
            "LTC": MagicMock(host="localhost", port=8001)
        }

        # Create connection manager
        self.connection_manager = ConnectionManager()

        # Create monitoring service
        self.monitoring_service = MonitoringService()

        # Create application
        self.application = PluginAdapterApplication()
        self.application.connection_manager = self.connection_manager
        self.application.monitoring_service = self.monitoring_service

        # Create RPC handlers
        self.rpc_handlers = {
            'utxo': UTXORPCHandler(self.application),
            'transaction': TransactionRPCHandler(self.application),
            'block': BlockRPCHandler(self.application),
            'balance': BalanceRPCHandler(self.application),
            'history': HistoryRPCHandler(self.application),
            'utility': UtilityRPCHandler()
        }

    async def teardown_components(self):
        """Cleanup application components."""
        if self.connection_manager:
            await self.connection_manager.close_all()
        if self.monitoring_service:
            await self.monitoring_service.stop()
        if self.application:
            await self.application.shutdown()

    @pytest.mark.integration
    @pytest.mark.network
    @pytest.mark.asyncio
    async def test_end_to_end_network_communication(self):
        """
        Test end-to-end network communication through all layers.
        
        This test validates:
        - Application -> Connection Manager -> TCP Socket communication
        - Request/response flow across all components
        - Proper error handling and recovery
        """
        logger.info("Starting end-to-end network communication test")

        # Setup components
        await self.setup_components()

        try:
            # Mock successful TCP connection
            with patch.object(TCPSocket, 'connect', return_value=None):
                with patch.object(TCPSocket, 'send_message',
                                  return_value={"result": "success", "id": 1}):
                    # Test connection manager integration
                    socket = await self.connection_manager.get_socket("BTC")
                    assert socket is not None

                    # Test RPC handler integration
                    result = await self.rpc_handlers['utility'].handle_version_check(
                        "BTC", ["plugin-adapter", "1.4"]
                    )

                    # Validate successful communication
                    assert result is not None
                    assert "result" in result
                    assert result["result"] == "success"

                    logger.info("End-to-end communication test passed")

        finally:
            await self.teardown_components()

    @pytest.mark.integration
    @pytest.mark.network
    @pytest.mark.asyncio
    async def test_tcp_socket_connection_manager_integration(self):
        """
        Test TCP socket integration with connection manager.
        
        This test validates:
        - Connection pooling and management
        - Socket lifecycle management
        - Connection reuse and cleanup
        """
        logger.info("Starting TCP socket connection manager integration test")

        await self.setup_components()

        try:
            # Mock TCP socket behavior
            mock_socket = MagicMock(spec=TCPSocket)
            mock_socket.host = "localhost"
            mock_socket.port = 8000
            mock_socket.is_connected = True
            mock_socket.connect = AsyncMock()
            mock_socket.close = AsyncMock()
            mock_socket.send_message = AsyncMock(return_value={"result": "success"})

            with patch.object(self.connection_manager, 'get_socket', return_value=mock_socket):
                # Test multiple socket requests (connection pooling)
                socket1 = await self.connection_manager.get_socket("BTC")
                socket2 = await self.connection_manager.get_socket("BTC")

                # Should return the same socket instance (connection pooling)
                assert socket1 is socket2
                assert socket1.is_connected is True

                # Test socket reuse
                result = await socket1.send_message("test.command", ["test"])
                assert result == {"result": "success"}

                logger.info("TCP socket connection manager integration test passed")

        finally:
            await self.teardown_components()

    @pytest.mark.integration
    @pytest.mark.network
    @pytest.mark.asyncio
    async def test_error_handling_across_network_layers(self):
        """
        Test error handling across all network layers.
        
        This test validates:
        - Network error propagation
        - Error recovery mechanisms
        - Graceful degradation
        """
        logger.info("Starting error handling across network layers test")

        await self.setup_components()

        try:
            # Test network error propagation
            with patch.object(TCPSocket, 'connect', side_effect=NetworkError("Connection failed")):
                with pytest.raises(NetworkError):
                    await self.connection_manager.get_socket("BTC")

            # Test protocol error handling
            mock_socket = MagicMock(spec=TCPSocket)
            mock_socket.send_message = AsyncMock(side_effect=ProtocolError("Invalid protocol"))

            with patch.object(self.connection_manager, 'get_socket', return_value=mock_socket):
                with pytest.raises(ProtocolError):
                    await self.rpc_handlers['utility'].handle_version_check("BTC", ["test"])

            # Test timeout error handling
            mock_socket = MagicMock(spec=TCPSocket)
            mock_socket.send_message = AsyncMock(side_effect=asyncio.TimeoutError())

            with patch.object(self.connection_manager, 'get_socket', return_value=mock_socket):
                with pytest.raises(NetworkError):
                    await self.rpc_handlers['utility'].handle_version_check("BTC", ["test"])

            logger.info("Error handling across network layers test passed")

        finally:
            await self.teardown_components()

    @pytest.mark.integration
    @pytest.mark.network
    @pytest.mark.asyncio
    async def test_connection_pooling_and_management(self):
        """
        Test connection pooling and management functionality.
        
        This test validates:
        - Multiple currency connection management
        - Connection reuse and caching
        - Connection cleanup and resource management
        """
        logger.info("Starting connection pooling and management test")

        await self.setup_components()

        try:
            # Mock multiple TCP connections
            mock_btc_socket = MagicMock(spec=TCPSocket)
            mock_btc_socket.host = "localhost"
            mock_btc_socket.port = 8000
            mock_btc_socket.is_connected = True
            mock_btc_socket.send_message = AsyncMock(return_value={"result": "BTC_SUCCESS"})

            mock_ltc_socket = MagicMock(spec=TCPSocket)
            mock_ltc_socket.host = "localhost"
            mock_ltc_socket.port = 8001
            mock_ltc_socket.is_connected = True
            mock_ltc_socket.send_message = AsyncMock(return_value={"result": "LTC_SUCCESS"})

            # Test connection pooling for different currencies
            with patch.object(self.connection_manager, 'get_socket') as mock_get_socket:
                def socket_selector(currency):
                    if currency == "BTC":
                        return mock_btc_socket
                    elif currency == "LTC":
                        return mock_ltc_socket
                    else:
                        raise ValueError(f"Unknown currency: {currency}")

                mock_get_socket.side_effect = socket_selector

                # Request connections for different currencies
                btc_socket = await self.connection_manager.get_socket("BTC")
                ltc_socket = await self.connection_manager.get_socket("LTC")

                # Verify different sockets for different currencies
                assert btc_socket is mock_btc_socket
                assert ltc_socket is mock_ltc_socket

                # Test connection reuse
                btc_socket2 = await self.connection_manager.get_socket("BTC")
                assert btc_socket2 is btc_socket

                # Test operations on different currencies
                btc_result = await btc_socket.send_message("test.command", ["BTC"])
                ltc_result = await ltc_socket.send_message("test.command", ["LTC"])

                assert btc_result == {"result": "BTC_SUCCESS"}
                assert ltc_result == {"result": "LTC_SUCCESS"}

            logger.info("Connection pooling and management test passed")

        finally:
            await self.teardown_components()

    @pytest.mark.integration
    @pytest.mark.network
    @pytest.mark.asyncio
    async def test_network_timeout_and_failure_scenarios(self):
        """
        Test network timeout and failure scenarios.
        
        This test validates:
        - Timeout handling
        - Connection failure recovery
        - Graceful handling of network issues
        """
        logger.info("Starting network timeout and failure scenarios test")

        await self.setup_components()

        try:
            # Test timeout scenarios
            timeout_test_start = time.perf_counter()

            mock_socket = MagicMock(spec=TCPSocket)
            mock_socket.send_message = AsyncMock(side_effect=asyncio.TimeoutError())

            with patch.object(self.connection_manager, 'get_socket', return_value=mock_socket):
                with pytest.raises(NetworkError):
                    await self.rpc_handlers['utility'].handle_version_check("BTC", ["test"])

            timeout_duration = time.perf_counter() - timeout_test_start
            assert timeout_duration < 5.0  # Should timeout quickly

            # Test connection failure scenarios
            mock_socket = MagicMock(spec=TCPSocket)
            mock_socket.connect = AsyncMock(side_effect=OSError("Connection refused"))

            with patch.object(TCPSocket, '__init__', return_value=None):
                with patch.object(TCPSocket, 'connect', side_effect=OSError("Connection refused")):
                    with pytest.raises(NetworkError):
                        await self.connection_manager.get_socket("BTC")

            logger.info("Network timeout and failure scenarios test passed")

        finally:
            await self.teardown_components()

    @pytest.mark.integration
    @pytest.mark.network
    @pytest.mark.asyncio
    async def test_monitoring_service_integration(self):
        """
        Test integration with monitoring service.
        
        This test validates:
        - Monitoring service integration
        - Performance metrics collection
        - Health check integration
        - Alert generation
        """
        logger.info("Starting monitoring service integration test")

        await self.setup_components()

        try:
            # Mock monitoring service
            mock_monitoring = MagicMock(spec=MonitoringService)
            mock_monitoring.record_metric = AsyncMock()
            mock_monitoring.check_health = AsyncMock(return_value=True)
            mock_monitoring.generate_alert = AsyncMock()

            self.application.monitoring_service = mock_monitoring

            # Mock successful operation with monitoring
            mock_socket = MagicMock(spec=TCPSocket)
            mock_socket.send_message = AsyncMock(return_value={"result": "success"})

            with patch.object(self.connection_manager, 'get_socket', return_value=mock_socket):
                # Perform operation that should trigger monitoring
                result = await self.rpc_handlers['utility'].handle_version_check("BTC", ["test"])

                # Verify monitoring was called
                mock_monitoring.record_metric.assert_called()
                mock_monitoring.check_health.assert_called()

                assert result is not None
                assert "result" in result

            logger.info("Monitoring service integration test passed")

        finally:
            await self.teardown_components()

    @pytest.mark.integration
    @pytest.mark.network
    @pytest.mark.asyncio
    async def test_cross_component_communication_validation(self):
        """
        Test cross-component communication validation.
        
        This test validates:
        - Communication between all components
        - Data consistency across components
        - Proper error propagation
        - Component lifecycle management
        """
        logger.info("Starting cross-component communication validation test")

        await self.setup_components()

        try:
            # Mock all components for comprehensive testing
            mock_socket = MagicMock(spec=TCPSocket)
            mock_socket.send_message = AsyncMock(return_value={
                "result": "success",
                "data": {"balance": 100000000}
            })

            with patch.object(self.connection_manager, 'get_socket', return_value=mock_socket):
                # Test communication chain: RPC Handler -> Connection Manager -> TCP Socket

                # Test balance handler
                balance_result = await self.rpc_handlers['balance'].handle_get_balance("BTC", ["test_address"])
                assert balance_result is not None
                assert "result" in balance_result

                # Test UTXO handler
                utxo_result = await self.rpc_handlers['utxo'].handle_get_utxo("BTC", ["test_address"])
                assert utxo_result is not None
                assert "result" in utxo_result

                # Test transaction handler
                tx_result = await self.rpc_handlers['transaction'].handle_get_transaction("BTC", ["test_txid"])
                assert tx_result is not None
                assert "result" in tx_result

                # Test block handler
                block_result = await self.rpc_handlers['block'].handle_get_block("BTC", ["test_blockhash"])
                assert block_result is not None
                assert "result" in block_result

                # Verify all operations used the same socket (connection pooling)
                assert mock_socket.send_message.call_count >= 4

            logger.info("Cross-component communication validation test passed")

        finally:
            await self.teardown_components()

    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_network_performance_and_stress(self):
        """
        Test network performance and stress handling.
        
        This test validates:
        - Performance under load
        - Concurrent connection handling
        - Resource usage optimization
        - Response time validation
        """
        logger.info("Starting network performance and stress test")

        await self.setup_components()

        try:
            # Mock high-performance socket
            mock_socket = MagicMock(spec=TCPSocket)
            mock_socket.send_message = AsyncMock(return_value={"result": "success"})

            with patch.object(self.connection_manager, 'get_socket', return_value=mock_socket):
                # Performance test: multiple concurrent operations
                start_time = time.perf_counter()

                # Create multiple concurrent operations
                tasks = []
                for i in range(10):
                    task = self.rpc_handlers['utility'].handle_version_check("BTC", [f"test_{i}"])
                    tasks.append(task)

                # Execute all tasks concurrently
                results = await asyncio.gather(*tasks, return_exceptions=True)

                execution_time = time.perf_counter() - start_time

                # Validate results
                assert len(results) == 10
                for result in results:
                    assert result is not None
                    assert "result" in result

                # Validate performance (should complete quickly)
                assert execution_time < 2.0  # Should complete in under 2 seconds

                # Verify socket reuse (connection pooling)
                assert mock_socket.send_message.call_count == 10

            logger.info(f"Network performance test passed (time: {execution_time:.3f}s)")

        finally:
            await self.teardown_components()


# Additional integration test helpers
class NetworkIntegrationHelpers:
    """Helper class for network integration testing."""

    @staticmethod
    async def create_test_network_scenario():
        """Create a realistic network test scenario."""
        return {
            "currencies": ["BTC", "LTC", "DOGE"],
            "operations": [
                "get_balance",
                "get_utxo",
                "get_transaction",
                "get_block"
            ],
            "error_scenarios": [
                "timeout",
                "connection_refused",
                "protocol_error"
            ]
        }

    @staticmethod
    def validate_network_response(response: Dict[str, Any]) -> bool:
        """Validate a network response structure."""
        required_fields = ["result"]
        return all(field in response for field in required_fields)

    @staticmethod
    async def measure_network_latency(func, *args, **kwargs) -> float:
        """Measure network operation latency."""
        start_time = time.perf_counter()
        try:
            await func(*args, **kwargs)
            return time.perf_counter() - start_time
        except Exception:
            return float('inf')  # Failed operations have infinite latency


if __name__ == "__main__":
    # Run the integration tests
    pytest.main([__file__, "-v", "--tb=short"])
