#!/usr/bin/env python3
"""
Operation Logger - Simplified Logging for Operations

This utility provides centralized, simple logging for all operations with minimal overhead.
"""

import logging
import time
import traceback
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class OperationLogger:
    """
    Simplified centralized logging utility for all operations.
    
    This utility provides consistent, minimal logging with only 3 methods:
    - start(): Log operation start and return timestamp
    - end(): Log operation end with duration
    - error(): Log operation errors
    """

    @staticmethod
    def start(operation: str, context: str = "system") -> int:
        """
        Log operation start and return timestamp.
        
        Args:
            operation: Operation name (e.g., "getutxos", "block_heights")
            context: Context for the operation (e.g., "BTC", "monitoring", "system")
            
        Returns:
            Start timestamp in milliseconds for use with end()
        """
        start_time = int(time.time() * 1000)
        logger.info("[%s] Sending %s", context, operation)
        return start_time

    @staticmethod
    def end(operation: str, start_time: int, context: str = "system") -> None:
        """
        Log operation end with duration.
        
        Args:
            operation: Operation name
            start_time: Start timestamp from start()
            context: Context for the operation
        """
        duration = int(time.time() * 1000) - start_time
        if duration < 1000:
            duration_str = f"{duration}ms"
        else:
            duration_str = f"{duration / 1000:.3f}s"

        logger.info("[%s] %s completed in %s", context, operation, duration_str)

    @staticmethod
    def warning(operation: str, context: str, error: Exception) -> None:
        """
        Log operation warning for non-critical issues.
        
        Args:
            operation: Operation name
            context: Context for the operation
            error: Exception that occurred
        """
        logger.warning("[%s] %s warning: %s", context, operation, str(error))

    @staticmethod
    def error(operation: str, context: str, error: Exception) -> None:
        """
        Log operation error.
        
        Args:
            operation: Operation name
            context: Context for the operation
            error: Exception that occurred
        """
        logger.error("[%s] %s failed: %s", context, operation, str(error))

    @staticmethod
    def success(operation: str, context: str, duration: int, data: Optional[Dict] = None) -> None:
        """
        Log successful operation completion at INFO level.
        
        Args:
            operation: Operation name (e.g., "getblockhash", "heartbeat")
            context: Context for the operation (e.g., "DASH", "monitoring")
            duration: Duration in milliseconds
            data: Optional data dictionary with context information
        """
        duration_str = f"{duration}ms" if duration < 1000 else f"{duration / 1000:.3f}s"

        if data:
            # Format data based on type - EXACT from original plan
            if 'height' in data:
                data_str = f"{data['currency']}:{data['height']}"
            elif 'fee' in data:
                data_str = f"{data['currency']}:{data['fee']}"
            elif 'success' in data:
                data_str = f"{data['currency']}:{data['success']}"
            else:
                data_str = str(data)
            logger.info("[%s] %s: %s | Failed: None | %s [OK]", context, operation, data_str, duration_str)
        else:
            logger.info("[%s] %s completed in %s [OK]", context, operation, duration_str)

    @staticmethod
    def debug_params(operation: str, context: str, params: List[Any]) -> None:
        """
        Log operation parameters at DEBUG level.
        
        Args:
            operation: Operation name
            context: Context for the operation
            params: List of parameters to log
        """
        if logger.isEnabledFor(logging.DEBUG):
            # Truncate large parameters to prevent spam
            truncated_params = []
            for param in params:
                param_str = str(param)
                if len(param_str) > 100:
                    truncated_params.append(f"{param_str[:97]}...")
                else:
                    truncated_params.append(param_str)

            logger.debug("[%s] %s: params=[%s]", context, operation, ", ".join(truncated_params))

    @staticmethod
    def debug_result(operation: str, context: str, result: Any, duration: int) -> None:
        """
        Log operation results at DEBUG level.
        
        Args:
            operation: Operation name
            context: Context for the operation
            result: Result to log
            duration: Duration in milliseconds
        """
        if logger.isEnabledFor(logging.DEBUG):
            duration_str = f"duration={duration}ms" if duration < 1000 else f"duration={duration / 1000:.3f}s"

            if isinstance(result, str):
                if len(result) > 64:
                    logger.debug("[%s] %s: result=%s... (len=%d), %s",
                                 context, operation, result[:64], len(result), duration_str)
                else:
                    logger.debug("[%s] %s: result=%s, %s", context, operation, result, duration_str)
            elif isinstance(result, dict) and 'tx_count' in result:
                logger.debug("[%s] %s: result_size=%d bytes, tx_count=%d, %s",
                             context, operation, len(str(result)), result['tx_count'], duration_str)
            elif isinstance(result, (int, float)):
                logger.debug("[%s] %s: result=%s, %s", context, operation, result, duration_str)
            else:
                logger.debug("[%s] %s: result=%s, %s", context, operation, result, duration_str)

    @staticmethod
    def debug_connection(host: str, port: int, status: str) -> None:
        """
        Log connection state changes at DEBUG level.
        
        Args:
            host: Host address
            port: Port number
            status: Connection status
        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Connection %s: %s:%d", status, host, port)

    @staticmethod
    def debug_error(operation: str, context: str, error: Exception) -> None:
        """
        Log detailed error information at DEBUG level.
        
        Args:
            operation: Operation name
            context: Context for the operation
            error: Exception that occurred
        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("[%s] %s: error=%s", context, operation, str(error))
            logger.debug("Traceback:\n%s", traceback.format_exc())
