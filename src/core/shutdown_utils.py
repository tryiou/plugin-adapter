#!/usr/bin/env python3

import asyncio
import logging
from typing import Awaitable, List

from src.core.constants import ShutdownConstants
from src.utils.operation_logger import OperationLogger

logger = logging.getLogger(__name__)


async def safe_task_cancellation(
        tasks: List[asyncio.Task],
        timeout: float = ShutdownConstants.TASK_CANCELLATION_TIMEOUT,
        component_name: str = "tasks"
) -> None:
    """
    Safely cancel multiple tasks with timeout and proper error handling.
    
    Args:
        tasks: List of asyncio tasks to cancel
        timeout: Timeout for task cancellation in seconds
        component_name: Name for logging purposes
    """
    if not tasks:
        return

    start = OperationLogger.start("cancel_tasks", "shutdown")

    # Cancel all tasks
    for task in tasks:
        if not task.done():
            task.cancel()

    # Wait for tasks to complete with timeout
    try:
        await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=timeout
        )
        OperationLogger.end("cancel_tasks", start, "shutdown")
    except asyncio.TimeoutError:
        OperationLogger.error("cancel_tasks", "shutdown", Exception(
            f"Some {component_name} did not cancel within {timeout}s timeout"))
    except Exception as e:
        OperationLogger.error("cancel_tasks", "shutdown", e)


async def safe_shutdown_operation(
        operation: Awaitable,
        timeout: float = ShutdownConstants.SHUTDOWN_TIMEOUT,
        operation_name: str = "operation"
) -> None:
    """
    Execute a shutdown operation with timeout and proper error handling.
    
    Args:
        operation: Async operation to execute
        timeout: Timeout for the operation in seconds
        operation_name: Name for logging purposes
    """
    start = OperationLogger.start(operation_name, "shutdown")
    try:
        await asyncio.wait_for(operation, timeout=timeout)
        OperationLogger.end(operation_name, start, "shutdown")
    except asyncio.TimeoutError:
        OperationLogger.error(operation_name, "shutdown",
                              Exception(f"Operation timed out after {timeout}s"))
        raise
    except Exception as e:
        OperationLogger.error(operation_name, "shutdown", e)
        raise


async def graceful_shutdown_sequence(
        shutdown_coroutines: List[Awaitable],
        timeout: float = ShutdownConstants.SHUTDOWN_TIMEOUT,
        sequence_name: str = "shutdown sequence"
) -> None:
    """
    Execute multiple shutdown operations concurrently with timeout.
    
    Args:
        shutdown_coroutines: List of shutdown coroutines to execute
        timeout: Timeout for the entire sequence in seconds
        sequence_name: Name for logging purposes
    """
    if not shutdown_coroutines:
        return

    start = OperationLogger.start(sequence_name, "shutdown")

    try:
        await asyncio.wait_for(
            asyncio.gather(*shutdown_coroutines, return_exceptions=True),
            timeout=timeout
        )
        OperationLogger.end(sequence_name, start, "shutdown")
    except asyncio.TimeoutError:
        OperationLogger.error(sequence_name, "shutdown",
                              Exception(f"Sequence timed out after {timeout}s"))
        raise
    except Exception as e:
        OperationLogger.error(sequence_name, "shutdown", e)
        raise
