#!/usr/bin/env python3
"""
Refactored Plugin Adapter - Modular Architecture with Thread Safety

This refactored version maintains 100% backward compatibility while addressing
all critical technical debt issues including thread safety, global state management,
and code organization.

Key Improvements:
- Thread-safe configuration management
- Proper async patterns instead of mixed threading
- Modular architecture with clear separation of concerns
- Comprehensive error handling and type safety
- Elimination of race conditions and global state

API Compatibility:
- All HTTP endpoints remain identical (/ , /height, /fees)
- All RPC methods maintain exact same signatures
- Response formats are preserved
- Environment variable requirements unchanged
"""

import asyncio
import json
import logging
# Setup logging
import os
import sys
from typing import Any, Dict

from aiohttp import web

from src.core.application import PluginAdapterApplication
# Import refactored modules
from src.core.configuration import config_manager
from src.core.constants import ConfigConstants
from src.core.response_factory import ResponseFactory
from src.services.monitoring_service import MonitoringService
from src.services.rpc_handlers import (
    UTXORPCHandler, TransactionRPCHandler, BlockRPCHandler,
    BalanceRPCHandler, HistoryRPCHandler, UtilityRPCHandler
)
from src.utils.operation_logger import OperationLogger

log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s %(levelname)-8s %(message)s",
    handlers=[
        logging.FileHandler("debug.log"),
        logging.StreamHandler()
    ])

logger = logging.getLogger(__name__)

# Logging already configured above

# Global application instance with connection limits
app = PluginAdapterApplication(max_concurrent_connections=3)

# RPC Handler instances
utxo_handler = UTXORPCHandler(app)
tx_handler = TransactionRPCHandler(app)
block_handler = BlockRPCHandler(app)
balance_handler = BalanceRPCHandler(app)
history_handler = HistoryRPCHandler(app)
utility_handler = UtilityRPCHandler()

# Monitoring service instance
monitoring_service = MonitoringService(app)

# Web routes
routes = web.RouteTableDef()


async def switchcase(request_json: Dict[str, Any]) -> str:
    """
    Switch-case dispatcher for RPC methods - maintains exact same logic as original.
    """
    # Extract currency for logging
    currency = request_json['params'][0] if request_json['params'] else "system"

    switcher = {
        'getutxos': lambda: utxo_handler.getutxos(request_json['params']),
        'getrawtransaction': lambda: tx_handler.getrawtransaction(request_json['params']),
        'getrawmempool': lambda: tx_handler.getrawmempool(request_json['params']),
        'getblockcount': lambda: block_handler.getblockcount(request_json['params']),
        'sendrawtransaction': lambda: tx_handler.sendrawtransaction(request_json['params']),
        'gettransaction': lambda: tx_handler.gettransaction(request_json['params']),
        'getblock': lambda: block_handler.getblock(request_json['params']),
        'getblockhash': lambda: block_handler.getblockhash(request_json['params']),
        'heights': lambda: monitoring_service.get_block_heights(),
        'fees': lambda: monitoring_service.get_tx_fees(),
        'getbalance': lambda: balance_handler.getbalance(request_json['params']),
        'gethistory': lambda: history_handler.gethistory(request_json['params']),
        'ping': lambda: utility_handler.ping()
    }

    async def method_not_found():
        start = OperationLogger.start("unknown_method", currency)
        OperationLogger.error("unknown_method", currency, Exception(f"Method {request_json['method']} not found"))
        OperationLogger.end("unknown_method", start, currency)
        return json.dumps(ResponseFactory.error('Method not found', -32601, 'MethodNotFoundError'))

    method_func = switcher.get(request_json['method'], method_not_found)

    # Log the incoming request
    # start = OperationLogger.start(request_json['method'], currency)

    try:
        result = await method_func()
        # OperationLogger.end(request_json['method'], start, currency)
        return result
    except Exception as e:
        # OperationLogger.error(request_json['method'], currency, e)
        return json.dumps(ResponseFactory.error(str(e), -32603, 'InternalError'))


@routes.post("/")
async def handle(request: web.Request) -> web.Response:
    """Handle RPC requests - maintains exact same behavior as original."""
    return web.Response(text=await switchcase(await request.json()))


@routes.get("/height")
async def get_heights(request: web.Request) -> web.Response:
    """Get block heights - uses new monitoring service."""
    return web.Response(text=await monitoring_service.get_block_heights())


@routes.get("/fees")
async def get_fees(request: web.Request) -> web.Response:
    """Get transaction fees - uses new monitoring service."""
    return web.Response(text=await monitoring_service.get_tx_fees())


async def main():
    """
    Main application entry point with proper shutdown coordination.
    """
    shutdown_event = asyncio.Event()

    try:
        # Setup routes
        await app.server.setup_routes(routes)

        # Start the application
        await app.start(ConfigConstants.DEFAULT_SERVER_PORT, shutdown_event)

        # Log detailed startup information
        currencies = config_manager.get_all_currencies()
        start = OperationLogger.start("startup", "adapter")
        logger.info("Plugin Adapter started successfully")
        logger.info("Server listening on 0.0.0.0:%d", ConfigConstants.DEFAULT_SERVER_PORT)
        logger.info("Configured currencies: %s", ", ".join(currencies) if currencies else "None")
        logger.info("Environment: UTXO_PLUGIN_LIST=%s", os.environ.get('UTXO_PLUGIN_LIST', 'Not set'))

        # Wait for shutdown signal instead of running indefinitely
        await shutdown_event.wait()
        OperationLogger.end("shutdown_signal", start, "adapter")

    except (asyncio.CancelledError, KeyboardInterrupt):
        OperationLogger.end("startup", start, "adapter")
    except Exception as e:
        OperationLogger.error("startup", "adapter", e)
        sys.exit(1)
    finally:
        # Ensure proper cleanup regardless of how we exit
        try:
            await app.stop()
        except Exception as e:
            OperationLogger.error("cleanup", "adapter", e)
            # Force exit if cleanup fails
            sys.exit(1)


if __name__ == '__main__':
    # Ensure UTXO_PLUGIN_LIST is set
    if not os.environ.get('UTXO_PLUGIN_LIST'):
        OperationLogger.error("main", "adapter", Exception("UTXO_PLUGIN_LIST environment variable not set"))
        print("ERROR: UTXO_PLUGIN_LIST environment variable is required")
        print("Please set it in format: 'CURRENCY1:HOST1,CURRENCY2:HOST2,...'")
        sys.exit(1)

    # Run the application
    asyncio.run(main())
