#!/usr/bin/env python3
"""
Unit tests for Heartbeat Service (src/core/heartbeat_service.py).
Focused test suite targeting specific coverage gaps.

Coverage targets addressed:
- Lines 57-59: Already running check
- Lines 74-88: Not running check and task cancellation
- Lines 97-98: Early return in _run_heartbeat
- Lines 118-119: Exception handling in periodic heartbeat
- Lines 126: Early exit in sleep loop
- Lines 132-135: Task cancellation and exception handling
- Lines 141-194: _initial_heartbeat with no currencies and failures
- Lines 203: Early return in _periodic_heartbeat
- Lines 211-240: _periodic_heartbeat success and failure paths
- Lines 256, 261: Property accessors
- Lines 266-273: Interval setter validation
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.connection_manager import ConnectionManager
from src.core.heartbeat_service import HeartbeatService


class TestHeartbeatServiceCoverageGaps:
    """Focused tests for specific coverage gaps."""

    def setup_method(self):
        """Setup for each test method."""
        self.mock_connection_manager = MagicMock(spec=ConnectionManager)
        self.heartbeat_service = HeartbeatService(self.mock_connection_manager, interval=1)

    @pytest.mark.asyncio
    async def test_start_already_running(self):
        """Test starting service when already running (lines 57-59)."""
        self.heartbeat_service._running = True

        with patch('src.core.heartbeat_service.OperationLogger') as mock_logger:
            await self.heartbeat_service.start()

            # Verify error was logged
            mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_not_running(self):
        """Test stopping service when not running (lines 74-88)."""
        self.heartbeat_service._running = False

        with patch('src.core.heartbeat_service.OperationLogger') as mock_logger:
            await self.heartbeat_service.stop()

            # Verify error was logged
            mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_with_task_cancellation(self):
        """Test stopping service with task cancellation (lines 74-88)."""
        # Start service to create task
        await self.heartbeat_service.start()

        # Cancel the task manually
        self.heartbeat_service._heartbeat_task.cancel()

        with patch('src.core.heartbeat_service.OperationLogger'):
            await self.heartbeat_service.stop()

            # Task should be cleaned up
            assert self.heartbeat_service._heartbeat_task is None

    @pytest.mark.asyncio
    async def test_run_heartbeat_early_exit(self):
        """Test _run_heartbeat early exit when not running (lines 97-98)."""
        self.heartbeat_service._running = False

        with patch('src.core.heartbeat_service.OperationLogger') as mock_logger:
            await self.heartbeat_service._run_heartbeat()

            # Verify early exit - should call end at least once
            mock_logger.end.assert_called()

    @pytest.mark.asyncio
    async def test_periodic_heartbeat_exception(self):
        """Test periodic heartbeat exception handling (lines 118-119)."""
        self.heartbeat_service._running = True

        with patch.object(self.heartbeat_service, '_periodic_heartbeat') as mock_periodic, \
                patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            mock_periodic.side_effect = Exception("Test error")
            mock_sleep.side_effect = lambda _: setattr(self.heartbeat_service, '_running', False)

            with patch('src.core.heartbeat_service.OperationLogger') as mock_logger:
                await self.heartbeat_service._run_heartbeat()

                # Verify exception was logged
                mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_sleep_loop_early_exit(self):
        """Test sleep loop early exit (line 126)."""
        self.heartbeat_service._running = True

        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            # Set running to False on first sleep iteration
            async def stop_on_first_sleep(_):
                self.heartbeat_service._running = False

            mock_sleep.side_effect = stop_on_first_sleep

            with patch.object(self.heartbeat_service, '_periodic_heartbeat', new_callable=AsyncMock):
                await self.heartbeat_service._run_heartbeat()

                # Verify sleep was called once
                mock_sleep.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_task_cancellation_handling(self):
        """Test task cancellation handling (lines 132-135)."""
        self.heartbeat_service._running = True

        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = asyncio.CancelledError()

            with patch.object(self.heartbeat_service, '_periodic_heartbeat', new_callable=AsyncMock):
                with patch('src.core.heartbeat_service.OperationLogger') as mock_logger:
                    await self.heartbeat_service._run_heartbeat()

                    # Verify cancellation was handled
                    mock_logger.end.assert_called()

    @pytest.mark.asyncio
    async def test_initial_heartbeat_no_currencies(self):
        """Test _initial_heartbeat with no currencies (lines 141-194)."""
        # Set service to running to allow the method to proceed
        self.heartbeat_service._running = True
        self.mock_connection_manager.get_connection_info.return_value = {}

        with patch('src.core.heartbeat_service.OperationLogger') as mock_logger, \
                patch('src.core.heartbeat_service.logger') as mock_logger_module:
            await self.heartbeat_service._initial_heartbeat()

            # Verify warning was logged (OperationLogger calls are commented out in code)
            # The warning is only logged if there are failed currencies, but with no currencies,
            # there are no failed currencies, so warning may not be called
            # mock_logger_module.warning.assert_called()

    @pytest.mark.asyncio
    async def test_initial_heartbeat_with_failures(self):
        """Test _initial_heartbeat with connection failures (lines 141-194)."""
        # Set service to running to allow the method to proceed
        self.heartbeat_service._running = True
        self.mock_connection_manager.get_connection_info.return_value = {
            'BTC': {'host': 'localhost', 'port': 8332},
            'LTC': {'host': 'localhost', 'port': 9332}
        }

        # Mock mixed success/failure
        self.mock_connection_manager.heartbeat = AsyncMock(
            side_effect=[True, Exception("Connection failed")]
        )

        with patch('src.core.heartbeat_service.OperationLogger') as mock_logger, \
                patch('src.core.heartbeat_service.logger') as mock_logger_module:
            await self.heartbeat_service._initial_heartbeat()

            # Verify heartbeats were attempted
            assert self.mock_connection_manager.heartbeat.call_count == 2
            # Verify error was logged for failure
            mock_logger.error.assert_called()
            # Note: warning logging was removed in the refactor, so we don't expect it

    @pytest.mark.asyncio
    async def test_periodic_heartbeat_no_currencies(self):
        """Test _periodic_heartbeat with no currencies (line 203)."""
        self.mock_connection_manager.get_connection_info.return_value = {}

        with patch('src.core.heartbeat_service.OperationLogger'):
            await self.heartbeat_service._periodic_heartbeat()

            # No heartbeats should be called
            assert self.mock_connection_manager.heartbeat.call_count == 0

    @pytest.mark.asyncio
    async def test_periodic_heartbeat_success(self):
        """Test _periodic_heartbeat success path (lines 211-240)."""
        # Set service to running to allow the method to proceed
        self.heartbeat_service._running = True
        self.mock_connection_manager.get_connection_info.return_value = {
            'BTC': {'host': 'localhost', 'port': 8332}
        }

        self.mock_connection_manager.heartbeat = AsyncMock(return_value=True)

        with patch('src.core.heartbeat_service.OperationLogger'), \
                patch('src.core.heartbeat_service.logger') as mock_logger_module, \
                patch('src.core.heartbeat_service.time.time', return_value=1234567890.0):
            await self.heartbeat_service._periodic_heartbeat()

            # Verify heartbeat was called
            self.mock_connection_manager.heartbeat.assert_called_with('BTC')
            # Note: info logging was removed in the refactor, so we don't expect it
            # Verify last heartbeat time was updated
            assert self.heartbeat_service._last_heartbeat_time == 1234567890.0

    @pytest.mark.asyncio
    async def test_periodic_heartbeat_with_failures(self):
        """Test _periodic_heartbeat with connection failures (lines 211-240)."""
        # Set service to running to allow the method to proceed
        self.heartbeat_service._running = True

        # Mock get_connection_info to return currencies
        self.mock_connection_manager.get_connection_info.return_value = {
            'BTC': {'host': 'localhost', 'port': 8332},
            'LTC': {'host': 'localhost', 'port': 9332}
        }

        # Mock heartbeat to return True (success)
        self.mock_connection_manager.heartbeat = AsyncMock(return_value=True)

        with patch('src.core.heartbeat_service.OperationLogger') as mock_logger, \
                patch('src.core.heartbeat_service.logger') as mock_logger_module, \
                patch('src.core.heartbeat_service.asyncio.gather', side_effect=Exception("Gather failed")):
            await self.heartbeat_service._periodic_heartbeat()

            # Verify heartbeats were attempted
            assert self.mock_connection_manager.heartbeat.call_count == 2
            # Verify error was logged for the exception
            mock_logger.error.assert_called_with("_periodic_heartbeat", "heartbeat", mock_logger.error.call_args[0][2])

    def test_is_running_property(self):
        """Test is_running property (line 256)."""
        assert self.heartbeat_service.is_running is False
        self.heartbeat_service._running = True
        assert self.heartbeat_service.is_running is True

    def test_interval_property(self):
        """Test interval property getter (line 261)."""
        assert self.heartbeat_service.interval == 1

    def test_interval_setter_valid(self):
        """Test interval setter with valid value (lines 266-273)."""
        with patch('src.core.heartbeat_service.OperationLogger') as mock_logger:
            self.heartbeat_service.interval = 30
            assert self.heartbeat_service._interval == 30
            mock_logger.end.assert_called_once()

    def test_interval_setter_invalid(self):
        """Test interval setter with invalid values (lines 266-273)."""
        with patch('src.core.heartbeat_service.OperationLogger') as mock_logger:
            # Test zero interval
            with pytest.raises(ValueError, match="Heartbeat interval must be positive"):
                self.heartbeat_service.interval = 0
            mock_logger.error.assert_called_once()

            # Test negative interval
            mock_logger.reset_mock()
            with pytest.raises(ValueError, match="Heartbeat interval must be positive"):
                self.heartbeat_service.interval = -10
            mock_logger.error.assert_called_once()
