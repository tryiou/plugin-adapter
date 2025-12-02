"""
Shared pytest fixtures and configuration for the plugin-adapter test suite.
"""

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest

# Import application modules for testing
from src.core.application import PluginAdapterApplication
from src.core.configuration import config_manager
from src.core.connection_manager import ConnectionManager
from src.networking.tcp_socket import TCPSocket
from src.services.monitoring_service import MonitoringService
from src.services.rpc_handlers import (BalanceRPCHandler, BlockRPCHandler,
                                       HistoryRPCHandler,
                                       TransactionRPCHandler,
                                       UtilityRPCHandler, UTXORPCHandler)

# Configure logging for tests
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


# Test markers for categorization
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")


# Shared fixtures
@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_data_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Provide sample configuration data."""
    return {
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


@pytest.fixture
async def clean_config_manager():
    """Provide a clean configuration manager for testing."""
    config_manager.clear()
    config_manager._coins = {
        "BTC": MagicMock(host="localhost", port=8000),
        "LTC": MagicMock(host="localhost", port=8001)
    }
    yield config_manager
    await config_manager.close()


@pytest.fixture
def mock_tcp_socket():
    """Provide a mock TCP socket for testing."""
    mock_socket = MagicMock(spec=TCPSocket)
    mock_socket.host = "localhost"
    mock_socket.port = 8000
    mock_socket.is_connected = True
    mock_socket.connect = AsyncMock()
    mock_socket.close = AsyncMock()
    mock_socket.send_message = AsyncMock()
    mock_socket.send_batch = AsyncMock()
    return mock_socket


@pytest.fixture
async def mock_connection_manager():
    """Provide a mock connection manager for testing."""
    manager = MagicMock(spec=ConnectionManager)
    manager.get_socket = AsyncMock()
    manager.reconnect = AsyncMock()
    manager.heartbeat = AsyncMock()
    manager.close_all = AsyncMock()
    manager.is_connected = MagicMock(return_value=True)
    return manager


@pytest.fixture
def mock_application(mock_connection_manager):
    """Provide a mock application instance for testing."""
    app = MagicMock(spec=PluginAdapterApplication)
    app.connection_manager = mock_connection_manager
    app.heartbeat_service = MagicMock(spec=MonitoringService)
    app.server = MagicMock()
    return app


@pytest.fixture
def rpc_handlers(mock_application):
    """Provide RPC handler instances for testing."""
    return {
        'utxo': UTXORPCHandler(mock_application),
        'transaction': TransactionRPCHandler(mock_application),
        'block': BlockRPCHandler(mock_application),
        'balance': BalanceRPCHandler(mock_application),
        'history': HistoryRPCHandler(mock_application),
        'utility': UtilityRPCHandler()
    }
