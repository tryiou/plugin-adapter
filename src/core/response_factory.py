#!/usr/bin/env python3
"""
Response Factory - Centralized Response Creation

This module provides a centralized factory for creating standardized API responses,
eliminating DRY violations and ensuring consistent response formats across the application.
"""

import json
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

import simplejson  # type: ignore

from src.core.errors import (ConfigurationError, NetworkError, ProtocolError,
                             TransactionError, ValidationError)

logger = logging.getLogger(__name__)


class ResponseFactory:
    """
    Centralized factory for creating standardized API responses.
    
    This factory eliminates DRY violations by providing a single source of truth
    for response creation across all RPC handlers and services.
    """

    @staticmethod
    def success(result: Any = None) -> Dict[str, Any]:
        """
        Create standardized success response.
        
        Args:
            result: The result data to include in the response
            
        Returns:
            Standardized success response dictionary
        """
        return {'result': result, 'error': None}

    @staticmethod
    def error(message: str, code: int = -1, error_type: str = "Error") -> Dict[str, Any]:
        """
        Create standardized error response.
        
        Args:
            message: Error message
            code: Error code
            error_type: Type of error
            
        Returns:
            Standardized error response dictionary
        """
        return {
            'result': None,
            'error': {
                'code': code,
                'message': message,
                'type': error_type
            }
        }

    @staticmethod
    def block_heights(heights: Dict[str, Optional[int]]) -> Dict[str, Any]:
        """
        Create block heights response.
        
        Args:
            heights: Dictionary mapping currencies to their block heights
            
        Returns:
            Standardized block heights response
        """
        return ResponseFactory.success(heights)

    @staticmethod
    def transaction_fees(fees: Dict[str, Optional[Decimal]]) -> Dict[str, Any]:
        """
        Create transaction fees response.
        
        Args:
            fees: Dictionary mapping currencies to their transaction fees
            
        Returns:
            Standardized transaction fees response
        """
        return ResponseFactory.success(fees)

    @staticmethod
    def utxos(utxos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create UTXOs response.
        
        Args:
            utxos: List of UTXO data
            
        Returns:
            Standardized UTXOs response
        """
        return ResponseFactory.success({"utxos": utxos})

    @staticmethod
    def balance(balance_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create balance response.
        
        Args:
            balance_data: Balance information
            
        Returns:
            Standardized balance response
        """
        return ResponseFactory.success(balance_data)

    @staticmethod
    def history(history_data: List[Any]) -> Dict[str, Any]:
        """
        Create transaction history response.
        
        Args:
            history_data: Transaction history data
            
        Returns:
            Standardized history response
        """
        return ResponseFactory.success(history_data)

    @staticmethod
    def transaction(tx_data: Any) -> Dict[str, Any]:
        """
        Create transaction response.
        
        Args:
            tx_data: Transaction data
            
        Returns:
            Standardized transaction response
        """
        return ResponseFactory.success(tx_data)

    @staticmethod
    def ping() -> Dict[str, Any]:
        """
        Create ping response.
        
        Returns:
            Standardized ping response
        """
        return ResponseFactory.success(1)

    @staticmethod
    def to_json(response: Dict[str, Any], use_simplejson: bool = False) -> str:
        """
        Convert response to JSON string.
        
        Args:
            response: Response dictionary
            use_simplejson: Whether to use simplejson for better decimal handling
            
        Returns:
            JSON string representation of the response
        """
        if use_simplejson:
            return simplejson.dumps(response)
        return json.dumps(response)

    # Convenience methods for common response patterns to eliminate DRY violations
    @staticmethod
    def create_success_response(result: Any = None) -> str:
        """
        Create and serialize a success response.
        
        Args:
            result: The result data to include in the response
            
        Returns:
            JSON string with success response
        """
        response = ResponseFactory.success(result)
        return json.dumps(response)

    @staticmethod
    def create_error_response(message: str, code: int = -1, error_type: str = "Error") -> str:
        """
        Create and serialize an error response.
        
        Args:
            message: Error message
            code: Error code
            error_type: Type of error
            
        Returns:
            JSON string with error response
        """
        response = ResponseFactory.error(message, code, error_type)
        return json.dumps(response)

    @staticmethod
    def create_utxos_response(utxos: List[Dict[str, Any]]) -> str:
        """
        Create and serialize a UTXOs response.
        
        Args:
            utxos: List of UTXO data
            
        Returns:
            JSON string with UTXOs response
        """
        response = ResponseFactory.utxos(utxos)
        return json.dumps(response)

    @staticmethod
    def create_balance_response(balance_data: Dict[str, Any]) -> str:
        """
        Create and serialize a balance response.
        
        Args:
            balance_data: Balance information
            
        Returns:
            JSON string with balance response
        """
        response = ResponseFactory.balance(balance_data)
        return json.dumps(response)

    @staticmethod
    def create_history_response(history_data: List[Any]) -> str:
        """
        Create and serialize a transaction history response.
        
        Args:
            history_data: Transaction history data
            
        Returns:
            JSON string with history response
        """
        response = ResponseFactory.history(history_data)
        return json.dumps(response)

    @staticmethod
    def create_transaction_response(tx_data: Any) -> str:
        """
        Create and serialize a transaction response.
        
        Args:
            tx_data: Transaction data
            
        Returns:
            JSON string with transaction response
        """
        response = ResponseFactory.transaction(tx_data)
        return json.dumps(response)

    @staticmethod
    def create_block_heights_response(heights: Dict[str, Optional[int]]) -> str:
        """
        Create and serialize a block heights response.
        
        Args:
            heights: Dictionary mapping currencies to their block heights
            
        Returns:
            JSON string with block heights response
        """
        response = ResponseFactory.block_heights(heights)
        return json.dumps(response)

    @staticmethod
    def create_transaction_fees_response(fees: Dict[str, Optional[Decimal]]) -> str:
        """
        Create and serialize a transaction fees response.
        
        Args:
            fees: Dictionary mapping currencies to their transaction fees
            
        Returns:
            JSON string with transaction fees response
        """
        response = ResponseFactory.transaction_fees(fees)
        return simplejson.dumps(response)

    @staticmethod
    def create_ping_response() -> str:
        """
        Create and serialize a ping response.
        
        Returns:
            JSON string with ping response
        """
        response = ResponseFactory.ping()
        return json.dumps(response)

    @staticmethod
    def create_error_from_exception(error: Union[NetworkError, ProtocolError, TransactionError,
    ValidationError, ConfigurationError, Exception]) -> str:
        """
        Create and serialize an error response from exception.
        
        Args:
            error: The exception that occurred
            
        Returns:
            JSON string error response
        """
        response = ResponseFactory.error_from_plugin_adapter_error(error)
        return json.dumps(response)

    @staticmethod
    def error_from_exception(error: Union[NetworkError, ProtocolError, TransactionError,
    ValidationError, ConfigurationError, Exception]) -> str:
        """
        Create error response from exception.
        
        Args:
            error: The exception that occurred
            
        Returns:
            JSON string error response
        """
        return json.dumps(ResponseFactory.error_from_plugin_adapter_error(error))

    @staticmethod
    def error_from_plugin_adapter_error(error: Union[NetworkError, ProtocolError, TransactionError,
    ValidationError, ConfigurationError, Exception]) -> Dict[str, Any]:
        """
        Create error response from PluginAdapterError.
        
        Args:
            error: The exception that occurred
            
        Returns:
            Standardized error response dictionary
        """
        # Handle different error types with appropriate attributes
        if hasattr(error, 'message'):
            message = error.message
        elif hasattr(error, 'args') and error.args:
            message = str(error.args[0])
        else:
            message = str(error)

        if hasattr(error, 'error_code'):
            error_code = error.error_code
        else:
            error_code = -1

        logger.error("[server] %s: %s", type(error).__name__, message)

        return {
            'result': None,
            'error': {
                'code': error_code,
                'message': message,
                'type': type(error).__name__
            }
        }
