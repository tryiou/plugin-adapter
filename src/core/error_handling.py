#!/usr/bin/env python3

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class PluginAdapterError(Exception):
    """Base exception class for plugin adapter errors."""

    def __init__(self, message: str, error_code: int = -1, original_error: Optional[Exception] = None):
        self.message = message
        self.error_code = error_code
        self.original_error = original_error
        super().__init__(self.message)


class NetworkError(PluginAdapterError):
    """Exception raised for network-related errors."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, error_code=-1, original_error=original_error)


class ProtocolError(PluginAdapterError):
    """Exception raised for protocol-related errors."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, error_code=-2, original_error=original_error)


class TransactionError(PluginAdapterError):
    """Exception raised for transaction-related errors."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, error_code=-25, original_error=original_error)


class ValidationError(PluginAdapterError):
    """Exception raised for validation errors."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, error_code=-5, original_error=original_error)


class ConfigurationError(PluginAdapterError):
    """Exception raised for configuration-related errors."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, error_code=-10, original_error=original_error)


def create_error_response(error: PluginAdapterError) -> Dict[str, Any]:
    """
    Create standardized error response format.
    
    Args:
        error: The error that occurred
        
    Returns:
        Standardized error response dictionary
    """
    logger.error(f"[server] {type(error).__name__}: {error.message}")

    return {
        'result': None,
        'error': {
            'code': error.error_code,
            'message': error.message,
            'type': type(error).__name__
        }
    }


def create_success_response(result: Any) -> Dict[str, Any]:
    """
    Create standardized success response format.
    
    Args:
        result: The result data
        
    Returns:
        Standardized success response dictionary
    """
    return {
        'result': result,
        'error': None
    }


def handle_exception(func):
    """
    Decorator to handle exceptions and return standardized error responses.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function with exception handling
    """

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except NetworkError as e:
            return create_error_response(e)
        except ProtocolError as e:
            return create_error_response(e)
        except TransactionError as e:
            return create_error_response(e)
        except ValidationError as e:
            return create_error_response(e)
        except ConfigurationError as e:
            return create_error_response(e)
        except Exception as e:
            # Wrap unexpected errors
            error = ProtocolError(f"Unexpected error: {str(e)}", e)
            return create_error_response(error)

    return wrapper
