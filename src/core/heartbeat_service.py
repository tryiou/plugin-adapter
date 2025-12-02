#!/usr/bin/env python3
"""
Heartbeat Service - Clean Architecture for Heartbeat Management

This service provides centralized heartbeat functionality that was previously
mixed into the ApplicationServer class. It follows the Single Responsibility
Principle by focusing solely on heartbeat operations.

Benefits:
- Better separation of concerns
- Easier testing and maintenance
- Cleaner ApplicationServer class
- Reusable heartbeat logic
"""

import asyncio
import logging
import time
from typing import Optional

from src.core.connection_manager import ConnectionManager
from src.utils.operation_logger import OperationLogger

logger = logging.getLogger(__name__)


class HeartbeatService:
    """
    Dedicated service for managing heartbeat operations.
    
    This service handles all heartbeat-related functionality including:
    - Initial connection checks
    - Periodic heartbeat monitoring
    - Connection health tracking
    - Graceful shutdown coordination
    """

    def __init__(self, connection_manager: ConnectionManager, interval: int = 15):
        """
        Initialize the heartbeat service.
        
        Args:
            connection_manager: Connection manager for accessing sockets
            interval: Heartbeat interval in seconds
        """
        self._connection_manager = connection_manager
        self._interval = interval
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._last_heartbeat_time = 0.0

    async def start(self) -> None:
        """Start the heartbeat monitoring."""
        start = OperationLogger.start("start", "heartbeat")

        if self._running:
            OperationLogger.error("start", "heartbeat", Exception("Heartbeat service is already running"))
            OperationLogger.end("start", start, "heartbeat")
            return

        self._running = True
        self._heartbeat_task = asyncio.create_task(self._run_heartbeat())
        OperationLogger.end("start", start, "heartbeat")

    async def stop(self) -> None:
        """Stop the heartbeat monitoring."""
        start = OperationLogger.start("stop", "heartbeat")

        if not self._running:
            OperationLogger.error("stop", "heartbeat", Exception("Heartbeat service is not running"))
            OperationLogger.end("stop", start, "heartbeat")
            return

        self._running = False

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
                OperationLogger.end("cancel", start, "heartbeat")
            except asyncio.CancelledError:
                OperationLogger.end("cancel", start, "heartbeat")
            except Exception as e:
                OperationLogger.error("cancel", "heartbeat", e)
            finally:
                self._heartbeat_task = None

        OperationLogger.end("stop", start, "heartbeat")

    async def _run_heartbeat(self) -> None:
        """Main heartbeat loop with shutdown coordination."""
        start = OperationLogger.start("_run_heartbeat", "heartbeat")

        try:
            # Check if we're still running before initial heartbeat
            if not self._running:
                OperationLogger.end("_run_heartbeat", start, "heartbeat")
                return

            # Initial connection check for all currencies
            # OperationLogger.start("_initial_heartbeat", "heartbeat")

            # Create a task for initial heartbeat so it can be cancelled
            # initial_task = asyncio.create_task(self._initial_heartbeat())

            # Wait for initial heartbeat with cancellation support
            # try:
            #     await initial_task
            # except asyncio.CancelledError:
            #     OperationLogger.end("_initial_heartbeat_cancelled", start, "heartbeat")
            #     return

            # Main heartbeat loop with shutdown coordination
            while self._running:
                OperationLogger.start("_periodic_heartbeat", "heartbeat")
                try:
                    await self._periodic_heartbeat()
                except Exception as e:
                    OperationLogger.error("_periodic_heartbeat", "heartbeat", e)

                # IMMEDIATE EXIT - use short sleep intervals to check shutdown flag frequently
                # Instead of sleeping for full interval, sleep in 1-second chunks
                try:
                    for _ in range(self._interval):
                        if not self._running:
                            break
                        await asyncio.sleep(1)
                except asyncio.CancelledError:
                    OperationLogger.end("_periodic_heartbeat_cancelled", start, "heartbeat")
                    break

        except asyncio.CancelledError:
            OperationLogger.end("_heartbeat_task_cancelled", start, "heartbeat")
        except Exception as e:
            OperationLogger.error("_heartbeat_task", "heartbeat", e)
        finally:
            OperationLogger.end("_heartbeat_stopped", start, "heartbeat")

    async def _initial_heartbeat(self) -> None:
        """Perform initial heartbeat for all configured currencies."""
        start = OperationLogger.start("_initial_heartbeat", "heartbeat")

        # Check if we're still running before proceeding
        if not self._running:
            OperationLogger.end("_initial_heartbeat", start, "heartbeat")
            return

        connection_info = await self._connection_manager.get_connection_info()
        currencies = connection_info.keys()
        if not currencies:
            OperationLogger.error("_initial_heartbeat", "heartbeat",
                                  Exception("No currencies configured for initial heartbeat"))
            OperationLogger.end("_initial_heartbeat", start, "heartbeat")
            return

        # Log initial heartbeat attempt with currency details using OperationLogger
        OperationLogger.debug_params("initial_heartbeat", "heartbeat", list(currencies))

        # Pre-allocate coroutine array for better memory efficiency
        coroutines = [self._connection_manager.heartbeat(currency) for currency in currencies]

        # Execute concurrently with cancellation support
        try:
            results = await asyncio.gather(*coroutines, return_exceptions=True)

            # Log results with currency details
            success_count = 0
            failed_currencies = []

            for i, currency in enumerate(currencies):
                result = results[i]
                if isinstance(result, Exception):
                    OperationLogger.error(currency, "system", result)
                    failed_currencies.append(currency)
                elif result:
                    success_count += 1
                    # Log successful initial heartbeat at INFO level
                    OperationLogger.success("Initial Heartbeat", currency, 0, {'currency': currency, 'height': 1})
                else:
                    OperationLogger.error(currency, "system", Exception("Initial heartbeat failed"))
                    failed_currencies.append(currency)

            # Log summary
            OperationLogger.debug_result("initial_heartbeat", "heartbeat", success_count, 0)
            if failed_currencies:
                OperationLogger.debug_error("initial_heartbeat", "heartbeat",
                                            Exception(f"Failed currencies: {', '.join(failed_currencies)}"))

        except asyncio.CancelledError:
            OperationLogger.end("_initial_heartbeat_cancelled", start, "heartbeat")
            raise
        except Exception as e:
            OperationLogger.error("_initial_heartbeat", "heartbeat", e)
        finally:
            OperationLogger.end("_initial_heartbeat", start, "heartbeat")

    async def _periodic_heartbeat(self) -> None:
        """Perform periodic heartbeat for all configured currencies."""
        # Check if we're still running before proceeding
        if not self._running:
            return

        connection_info = await self._connection_manager.get_connection_info()
        currencies = connection_info.keys()
        if not currencies:
            return

        start_time = time.time()

        # Execute heartbeat checks
        try:
            coroutines = [self._connection_manager.heartbeat(currency) for currency in currencies]
            results = await asyncio.gather(*coroutines, return_exceptions=True)

            # Count results
            success_count = sum(1 for r in results if not isinstance(r, Exception) and r)
            failed_currencies = []
            for i, currency in enumerate(currencies):
                result = results[i]
                if isinstance(result, Exception) or not result:
                    failed_currencies.append(currency)

            # Update timing and log comprehensive summary
            self._last_heartbeat_time = time.time()
            duration = self._last_heartbeat_time - start_time
            duration_ms = int(duration * 1000)

            # Log INFO level currency status summary for each currency
            for currency in currencies:
                currency_result = 1 if currency not in failed_currencies else 0
                currency_failed = currency if currency in failed_currencies else None

                OperationLogger.success("Heartbeat", currency, duration_ms,
                                        {'currency': currency, 'height': currency_result,
                                         'failed': currency_failed})

            # Add conditional DEBUG logging (only on failure or slow response >100ms)
            if failed_currencies or duration_ms > 100:
                if logger.isEnabledFor(logging.DEBUG):
                    OperationLogger.debug_params("heartbeat", ', '.join(currencies), list(currencies))
                    OperationLogger.debug_result("heartbeat", ', '.join(currencies), success_count, duration_ms)

        except asyncio.CancelledError as e:
            OperationLogger.error("_periodic_heartbeat_cancelled", "heartbeat", Exception(str(e)))
            raise
        except Exception as e:
            OperationLogger.error("_periodic_heartbeat", "heartbeat", e)
            # Log error details at DEBUG level
            if logger.isEnabledFor(logging.DEBUG):
                OperationLogger.debug_error("_periodic_heartbeat", "heartbeat", e)

    def get_status(self) -> dict:
        """Get current heartbeat service status."""
        return {
            'running': self._running,
            'interval': self._interval,
            'last_heartbeat': self._last_heartbeat_time,
            'uptime': time.time() - self._last_heartbeat_time if self._last_heartbeat_time > 0 else 0
        }

    @property
    def is_running(self) -> bool:
        """Check if the heartbeat service is running."""
        return self._running

    @property
    def interval(self) -> int:
        """Get the heartbeat interval."""
        return self._interval

    @interval.setter
    def interval(self, value: int) -> None:
        """Set the heartbeat interval."""
        start = OperationLogger.start("set_interval", "heartbeat")

        if value <= 0:
            OperationLogger.error("set_interval", "heartbeat", ValueError("Heartbeat interval must be positive"))
            raise ValueError("Heartbeat interval must be positive")

        self._interval = value
        OperationLogger.end("set_interval", start, "heartbeat")
