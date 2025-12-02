#!/usr/bin/env python3
"""
ResponseHelper - Centralized Response Creation Utility

This utility provides a centralized interface for creating standardized API responses,
eliminating DRY violations and ensuring consistent response formats across the application.
It wraps ResponseFactory to provide a cleaner, more maintainable interface.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

from src.core.errors import (ConfigurationError, NetworkError, ProtocolError,
                             TransactionError, ValidationError)
from src.core.response_factory import ResponseFactory

logger = logging.getLogger(__name__)


class ResponseHelper:
    """
    Centralized utility for creating standardized API responses.
    
    This helper eliminates DRY violations by providing a single source of truth
    for response creation across all handlers and services, wrapping ResponseFactory
    with a cleaner interface.
    """

    @staticmethod
    def success(result: Any = None) -> str:
        """
        Create standardized success response.
        
        Args:
            result: The result data to include in the response
            
        Returns:
            JSON string with success response
        """
        return ResponseFactory.create_success_response(result)

    @staticmethod
    def error(message: str, code: int = -1, error_type: str = "Error") -> str:
        """
        Create standardized error response.
        
        Args:
            message: Error message
            code: Error code
            error_type: Type of error
            
        Returns:
            JSON string with error response
        """
        return ResponseFactory.create_error_response(message, code, error_type)

    @staticmethod
    def block_heights(heights: Dict[str, Optional[int]]) -> str:
        """
        Create block heights response.
        
        Args:
            heights: Dictionary mapping currencies to their block heights
            
        Returns:
            JSON string with block heights response
        """
        return ResponseFactory.create_block_heights_response(heights)

    @staticmethod
    def transaction_fees(fees: Dict[str, Optional[Decimal]]) -> str:
        """
        Create transaction fees response.
        
        Args:
            fees: Dictionary mapping currencies to their transaction fees
            
        Returns:
            JSON string with transaction fees response
        """
        return ResponseFactory.create_transaction_fees_response(fees)

    @staticmethod
    def utxos(utxos: List[Dict[str, Any]]) -> str:
        """
        Create UTXOs response.
        
        Args:
            utxos: List of UTXO data
            
        Returns:
            JSON string with UTXOs response
        """
        return ResponseFactory.create_utxos_response(utxos)

    @staticmethod
    def balance(balance_data: Dict[str, Any]) -> str:
        """
        Create balance response.
        
        Args:
            balance_data: Balance information
            
        Returns:
            JSON string with balance response
        """
        return ResponseFactory.create_balance_response(balance_data)

    @staticmethod
    def history(history_data: List[Any]) -> str:
        """
        Create transaction history response.
        
        Args:
            history_data: Transaction history data
            
        Returns:
            JSON string with history response
        """
        return ResponseFactory.create_history_response(history_data)

    @staticmethod
    def transaction(tx_data: Any) -> str:
        """
        Create transaction response.
        
        Args:
            tx_data: Transaction data
            
        Returns:
            JSON string with transaction response
        """
        return ResponseFactory.create_transaction_response(tx_data)

    @staticmethod
    def ping() -> str:
        """
        Create ping response.
        
        Returns:
            JSON string with ping response
        """
        return ResponseFactory.create_ping_response()

    @staticmethod
    def from_exception(error: Union[NetworkError, ProtocolError, TransactionError,
    ValidationError, ConfigurationError, Exception]) -> str:
        """
        Create error response from exception.
        
        Args:
            error: The exception that occurred
            
        Returns:
            JSON string error response
        """
        return ResponseFactory.create_error_from_exception(error)

    @staticmethod
    def error_from_plugin_adapter_error(error: Union[NetworkError, ProtocolError, TransactionError,
    ValidationError, ConfigurationError, Exception]) -> str:
        """
        Create error response from PluginAdapterError.
        
        Args:
            error: The exception that occurred
            
        Returns:
            JSON string error response
        """
        return ResponseFactory.error_from_exception(error)

    # Convenience methods for common error scenarios
    @staticmethod
    def validation_error(message: str) -> str:
        """
        Create validation error response.
        
        Args:
            message: Validation error message
            
        Returns:
            JSON string with validation error response
        """
        return ResponseHelper.error(message, code=-32602, error_type="ValidationError")

    @staticmethod
    def network_error(message: str) -> str:
        """
        Create network error response.
        
        Args:
            message: Network error message
            
        Returns:
            JSON string with network error response
        """
        return ResponseHelper.error(message, code=-32603, error_type="NetworkError")

    @staticmethod
    def protocol_error(message: str) -> str:
        """
        Create protocol error response.
        
        Args:
            message: Protocol error message
            
        Returns:
            JSON string with protocol error response
        """
        return ResponseHelper.error(message, code=-32603, error_type="ProtocolError")

    @staticmethod
    def not_found_error(message: str = "Resource not found") -> str:
        """
        Create not found error response.
        
        Args:
            message: Not found error message
            
        Returns:
            JSON string with not found error response
        """
        return ResponseHelper.error(message, code=-32601, error_type="NotFoundError")

    @staticmethod
    def internal_error(message: str = "Internal server error") -> str:
        """
        Create internal error response.
        
        Args:
            message: Internal error message
            
        Returns:
            JSON string with internal error response
        """
        return ResponseHelper.error(message, code=-32603, error_type="InternalError")
