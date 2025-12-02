#!/usr/bin/env python3

import logging
from typing import Any, Dict

from src.core.errors import (ConfigurationError, NetworkError,
                             PluginAdapterError, ProtocolError,
                             TransactionError, ValidationError)
from src.core.response_factory import ResponseFactory

logger = logging.getLogger(__name__)


class ErrorHandler:
    """
    Dedicated service class for handling errors consistently across the application.
    
    This class provides centralized error handling logic that can be reused
    across different parts of the application, reducing code duplication and
    improving maintainability.
    """

    @staticmethod
    def handle_error(error: PluginAdapterError) -> Dict[str, Any]:
        """
        Handle a PluginAdapterError and return standardized response.
        
        Args:
            error: The error that occurred
            
        Returns:
            Standardized error response dictionary
        """
        return ResponseFactory.error_from_plugin_adapter_error(error)

    @staticmethod
    def handle_unexpected_error(original_error: Exception) -> Dict[str, Any]:
        """
        Handle unexpected errors by wrapping them in a ProtocolError.
        
        Args:
            original_error: The original unexpected error
            
        Returns:
            Standardized error response dictionary
        """
        error = ProtocolError(f"Unexpected error: {str(original_error)}", original_error)
        return ResponseFactory.error_from_plugin_adapter_error(error)

    @staticmethod
    def handle_rpc_method_exceptions(func):
        """
        Decorator to handle exceptions in RPC methods with reduced nesting.
        
        Args:
            func: Function to wrap
            
        Returns:
            Wrapped function with exception handling
        """

        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (NetworkError, ProtocolError, TransactionError, ValidationError, ConfigurationError) as e:
                return ErrorHandler.handle_error(e)
            except Exception as e:
                return ErrorHandler.handle_unexpected_error(e)

        return wrapper
