#!/usr/bin/env python3
"""
Parameter Validation Service - Centralized Validation Logic

This module provides centralized parameter validation for RPC methods,
eliminating duplication and ensuring consistent validation across all handlers.
"""

import logging
from typing import Any, List, Optional

from src.core.error_handling import ValidationError

logger = logging.getLogger(__name__)


class ParameterValidator:
    """
    Centralized parameter validation service for RPC methods.
    
    This service eliminates DRY violations by providing a single source of truth
    for parameter validation logic across all RPC handlers.
    """

    @staticmethod
    def validate_rpc_params(params: List[Any], min_length: int = 1) -> Optional[ValidationError]:
        """
        Validate RPC method parameters.
        
        Args:
            params: Parameters to validate
            min_length: Minimum required length for params list
            
        Returns:
            ValidationError if validation fails, None if valid
        """
        if not params or not isinstance(params, list) or len(params) < min_length:
            return ValidationError("Invalid parameters")

        currency = params[0]
        if not currency or not isinstance(currency, str):
            return ValidationError("Invalid currency parameter")

        return None

    @staticmethod
    def validate_addresses(raw_addresses: Any) -> List[str]:
        """
        Extract and validate addresses from various input formats.
        
        Args:
            raw_addresses: Raw addresses in various formats (string, list, JSON string)
            
        Returns:
            List of validated address strings
            
        Raises:
            ValidationError: If addresses cannot be parsed or are invalid
        """
        if not raw_addresses:
            return []

        # Handle JSON string
        if isinstance(raw_addresses, str):
            try:
                import json
                raw_addresses = json.loads(raw_addresses)
            except json.JSONDecodeError:
                # If not valid JSON, treat as comma-separated string
                raw_addresses = raw_addresses.split(',')

        # Validate list format
        if not isinstance(raw_addresses, list):
            return []

        # Clean and validate addresses
        addresses = []
        for addr in raw_addresses:
            if isinstance(addr, str) and addr.strip():
                addresses.append(addr.strip())

        return addresses

    @staticmethod
    def validate_transaction_params(params: List[Any]) -> Optional[ValidationError]:
        """
        Validate transaction-related RPC parameters.
        
        Args:
            params: Parameters to validate
            
        Returns:
            ValidationError if validation fails, None if valid
        """
        # First check currency parameter (required for all operations)
        if not params or not isinstance(params, list) or len(params) < 1:
            return ValidationError("Invalid parameters")

        currency = params[0]
        if not currency or not isinstance(currency, str):
            return ValidationError("Invalid currency parameter")

        # Then check transaction-specific requirements
        if len(params) < 2:
            return ValidationError("Invalid raw transaction")

        rawtx = params[1]
        if not rawtx or not isinstance(rawtx, str):
            return ValidationError("Invalid raw transaction")

        return None

    @staticmethod
    def validate_block_params(params: List[Any]) -> Optional[ValidationError]:
        """
        Validate block-related RPC parameters.
        
        Args:
            params: Parameters to validate
            
        Returns:
            ValidationError if validation fails, None if valid
        """
        # First check currency parameter (required for all operations)
        if not params or not isinstance(params, list) or len(params) < 1:
            return ValidationError("Invalid parameters")

        currency = params[0]
        if not currency or not isinstance(currency, str):
            return ValidationError("Invalid currency parameter")

        # Then check block-specific requirements
        if len(params) < 2:
            return ValidationError("Block hash/height parameter is required")

        block_param = params[1]
        if not block_param:
            return ValidationError("Block hash/height parameter is required")

        return None

    @staticmethod
    def validate_balance_params(params: List[Any]) -> Optional[ValidationError]:
        """
        Validate balance-related RPC parameters.
        
        Args:
            params: Parameters to validate
            
        Returns:
            ValidationError if validation fails, None if valid
        """
        # First check currency parameter (required for all operations)
        if not params or not isinstance(params, list) or len(params) < 1:
            return ValidationError("Invalid parameters")

        currency = params[0]
        if not currency or not isinstance(currency, str):
            return ValidationError("Invalid currency parameter")

        # Then check balance-specific requirements
        if len(params) < 2:
            return ValidationError("Invalid address parameter")

        address = params[1]
        if not address or not isinstance(address, str):
            return ValidationError("Invalid address parameter")

        return None


def validate_rpc_parameters(params: List[Any], min_length: int = 1) -> Optional[ValidationError]:
    """
    Convenience function for validating RPC parameters.
    
    Args:
        params: Parameters to validate
        min_length: Minimum required length for params list
        
    Returns:
        ValidationError if validation fails, None if valid
    """
    return ParameterValidator.validate_rpc_params(params, min_length)


def validate_address_list(raw_addresses: Any) -> List[str]:
    """
    Convenience function for validating address lists.
    
    Args:
        raw_addresses: Raw addresses in various formats
        
    Returns:
        List of validated address strings
    """
    return ParameterValidator.validate_addresses(raw_addresses)
