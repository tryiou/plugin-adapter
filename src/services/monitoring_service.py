#!/usr/bin/env python3
"""
Monitoring Service - Clean Architecture for Monitoring Endpoints

This service provides a clean interface for monitoring endpoints that:
- Eliminates circular imports by not depending on helpers.py
- Uses existing RPC handlers for consistent error handling
- Follows Single Responsibility Principle
- Provides clear separation between monitoring and RPC logic

Dependencies:
- plugin-adapter.py → monitoring_service.py → rpc_handlers.py (clean flow)
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Dict, Optional

from src.core.application import PluginAdapterApplication
from src.core.configuration import config_manager
from src.services.rpc_handlers import BlockRPCHandler, TransactionRPCHandler
from src.utils.operation_logger import OperationLogger
from src.utils.response_helper import ResponseHelper

logger = logging.getLogger(__name__)


class MonitoringServiceInterface(ABC):
    """
    Interface for monitoring services to enable dependency injection and loose coupling.
    
    This interface defines the contract for monitoring operations, allowing for
    different implementations and easier testing through dependency injection.
    """

    @abstractmethod
    async def get_block_heights(self) -> str:
        """
        Get block heights for all configured currencies.
        
        Returns:
            JSON string with heights mapping currencies to their block counts
        """
        pass

    @abstractmethod
    async def get_tx_fees(self) -> str:
        """
        Get transaction fees for all configured currencies.
        
        Returns:
            JSON string with fees mapping currencies to their relay fees
        """
        pass


class MonitoringService(MonitoringServiceInterface):
    """
    Service that orchestrates monitoring operations using existing RPC handlers.
    
    This service provides a clean interface for monitoring endpoints that:
    - Uses existing RPC handlers for consistent behavior
    - Eliminates circular imports
    - Follows Single Responsibility Principle
    - Provides centralized error handling
    """

    def __init__(self, app: PluginAdapterApplication,
                 block_handler: Optional[BlockRPCHandler] = None,
                 tx_handler: Optional[TransactionRPCHandler] = None):
        """
        Initialize the monitoring service with dependency injection.
        
        Args:
            app: Application instance providing access to connection manager
            block_handler: Optional BlockRPCHandler instance (dependency injection)
            tx_handler: Optional TransactionRPCHandler instance (dependency injection)
        """
        self.app = app
        # Use injected handlers or create new ones for backward compatibility
        self.block_handler = block_handler if block_handler is not None else BlockRPCHandler(app)
        self.tx_handler = tx_handler if tx_handler is not None else TransactionRPCHandler(app)

    async def get_block_heights(self) -> str:
        """
        Get block heights for all configured currencies.
        
        Orchestrates block height collection using the existing BlockRPCHandler,
        ensuring consistent error handling and connection management.
        
        Returns:
            JSON string with heights mapping currencies to their block counts
        """
        heights: Dict[str, Optional[int]] = {}
        start = OperationLogger.start("block_heights", "monitoring")

        currencies = config_manager.get_all_currencies()
        if not currencies:
            OperationLogger.error("get_block_heights", "system", Exception("No currencies configured"))
            return ResponseHelper.block_heights(heights)

        # Create coroutines for all currencies using existing RPC handlers
        # Wrap each coroutine to return both currency and result for as_completed
        async def get_height_with_currency(currency):
            try:
                result = await self._get_block_height_for_currency(currency)
                return currency, result
            except Exception as e:
                OperationLogger.error("get_block_heights", currency, e)
                return currency, None

        coroutines = [get_height_with_currency(currency) for currency in currencies]

        # Execute concurrently with exception handling using as_completed for better performance
        heights = {currency: None for currency in currencies}  # Initialize all currencies to None

        # Process results as they complete for better response times
        tasks = [asyncio.create_task(coro) for coro in coroutines]

        # Process results as they complete
        for task in asyncio.as_completed(tasks):
            try:
                currency, result = await task
                heights[currency] = result
            except Exception as e:
                OperationLogger.error("get_block_heights", "system", e)
                # Keep the None value for this currency
                pass

        # Log aggregated results
        successful_currencies = [k for k, v in heights.items() if v is not None]
        if successful_currencies:
            height_info = ", ".join([f"{k}={v}" for k, v in heights.items() if v is not None])
            logger.info("[monitoring] Block heights: %s", height_info)

        OperationLogger.end("block_heights", start, "monitoring")

        return ResponseHelper.block_heights(heights)

    async def _get_block_height_for_currency(self, currency: str) -> Optional[int]:
        """
        Get block height for a specific currency using RPC handler.
        
        Args:
            currency: Currency symbol
            
        Returns:
            Block height or None if failed
            
        Raises:
            Exception: For any errors during the operation
        """
        start = OperationLogger.start("_get_block_height_for_currency", currency)

        try:
            # Use existing RPC handler which has @ensure_connected decorator
            # This ensures consistent connection management and error handling
            result_json = await self.block_handler.getblockcount([currency])

            # Parse the JSON response
            result = self._parse_rpc_response(result_json)

            if result is None:
                OperationLogger.error("_get_block_height_for_currency", currency,
                                      Exception("Block height returned None"))
                return None

            # Calculate duration
            duration_ms = int(time.time() * 1000) - start

            # Replace with single INFO line for production:
            OperationLogger.success("Heights", "monitoring", duration_ms,
                                    {'currency': currency, 'height': result, 'failed': 'None'})

            # Add DEBUG logging for troubleshooting:
            OperationLogger.debug_params("getblockcount", currency, [currency])
            OperationLogger.debug_result("getblockcount", currency, result, duration_ms)

            return result

        except Exception as e:
            OperationLogger.error("_get_block_height_for_currency", currency, e)
            raise

    async def get_tx_fees(self) -> str:
        """
        Get transaction fees for all configured currencies.
        
        Orchestrates fee collection using the existing TransactionRPCHandler,
        ensuring consistent error handling and connection management.
        
        Returns:
            JSON string with fees mapping currencies to their relay fees
        """
        fees: Dict[str, Optional[Decimal]] = {}
        start = OperationLogger.start("transaction_fees", "monitoring")

        currencies = config_manager.get_all_currencies()
        if not currencies:
            OperationLogger.error("get_tx_fees", "system", Exception("No currencies configured"))
            return ResponseHelper.transaction_fees(fees)

        # Create coroutines for all currencies using existing RPC handlers
        # Wrap each coroutine to return both currency and result for as_completed
        async def get_fee_with_currency(currency):
            try:
                result = await self._get_tx_fee_for_currency(currency)
                return currency, result
            except Exception as e:
                OperationLogger.error("get_tx_fees", currency, e)
                return currency, None

        coroutines = [get_fee_with_currency(currency) for currency in currencies]

        # Execute concurrently with exception handling using as_completed for better performance
        fees = {currency: None for currency in currencies}  # Initialize all currencies to None

        # Process results as they complete for better response times
        tasks = [asyncio.create_task(coro) for coro in coroutines]

        # Process results as they complete
        for task in asyncio.as_completed(tasks):
            try:
                currency, result = await task
                fees[currency] = result
            except Exception as e:
                OperationLogger.error("get_tx_fees", "system", e)
                # Keep the None value for this currency
                pass

        # Log aggregated results
        successful_currencies = [k for k, v in fees.items() if v is not None]
        if successful_currencies:
            fee_info = ", ".join([f"{k}={v}" for k, v in fees.items() if v is not None])
            logger.info("[monitoring] Transaction fees: %s", fee_info)

        OperationLogger.end("transaction_fees", start, "monitoring")

        return ResponseHelper.transaction_fees(fees)

    async def _get_tx_fee_for_currency(self, currency: str) -> Optional[Decimal]:
        """
        Get transaction fee for a specific currency using RPC handler.
        
        Args:
            currency: Currency symbol
            
        Returns:
            Transaction fee as Decimal or None if failed
            
        Raises:
            Exception: For any errors during the operation
        """
        start = OperationLogger.start("_get_tx_fee_for_currency", currency)

        try:
            # Use existing RPC handler which has @ensure_connected decorator
            # This ensures consistent connection management and error handling
            result_json = await self.tx_handler.get_plugin_fees([currency])

            # Parse the JSON response
            result = self._parse_rpc_response(result_json)

            if result is None:
                OperationLogger.error("_get_tx_fee_for_currency", currency,
                                      Exception("Transaction fee returned None"))
                return None

            # Convert to Decimal with proper formatting
            fee_decimal = Decimal('{:.8f}'.format(float(result)))

            # Calculate duration
            duration_ms = int(time.time() * 1000) - start

            # Replace with single INFO line for production:
            OperationLogger.success("Fees", "monitoring", duration_ms,
                                    {'currency': currency, 'fee': fee_decimal, 'failed': 'None'})

            # Add DEBUG logging for troubleshooting:
            OperationLogger.debug_params("get_plugin_fees", currency, [currency])
            OperationLogger.debug_result("get_plugin_fees", currency, fee_decimal, duration_ms)

            return fee_decimal

        except Exception as e:
            OperationLogger.error("_get_tx_fee_for_currency", currency, e)
            raise

    def _parse_rpc_response(self, response_json: str) -> Optional[Any]:
        """
        Parse JSON response from RPC handler.
        
        Args:
            response_json: JSON string response from RPC handler
            
        Returns:
            Parsed result or None if error
        """
        # start = OperationLogger.start("_parse_rpc_response", "system")

        try:
            response = self._parse_json_safely(response_json)

            # Check for error in response
            if response and 'error' in response and response['error'] is not None:
                OperationLogger.error("_parse_rpc_response", "system", Exception(response['error']))
                return None

            # Return the result
            # OperationLogger.end("_parse_rpc_response", start, "system")
            return response.get('result') if response else None

        except Exception as e:
            OperationLogger.error("_parse_rpc_response", "system", e)
            return None

    def _parse_json_safely(self, json_str: str) -> Optional[Dict[str, Any]]:
        """
        Safely parse JSON string.
        
        Args:
            json_str: JSON string to parse
            
        Returns:
            Parsed dictionary or None if parsing fails
        """
        # start = OperationLogger.start("_parse_json_safely", "system")

        try:
            import json
            result = json.loads(json_str)
            # OperationLogger.end("_parse_json_safely", start, "system")
            return result
        except (ValueError, TypeError) as e:
            OperationLogger.error("_parse_json_safely", "system", e)
            return None
