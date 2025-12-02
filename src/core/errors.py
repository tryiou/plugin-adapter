from typing import Optional


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
