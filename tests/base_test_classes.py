"""
Base Test Classes for Plugin-Adapter Testing Framework

This module provides base test classes that encapsulate common testing patterns,
utilities, and setup/teardown logic for different types of tests (unit, integration, e2e).
"""

import asyncio
import logging
import time
from abc import ABC
from typing import Any, Dict, List, Optional, Type, Union
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.fixtures.mock_configuration_manager import MockConfigurationManager

# Mock imports removed - using standard unittest.mock instead

logger = logging.getLogger(__name__)


class BaseTestCase(ABC):
    """
    Base test case class that provides common functionality for all test types.
    
    This class provides:
    - Common setup and teardown patterns
    - Test data management
    - Error handling and reporting
    - Performance tracking
    - Mock management
    """

    def __init__(self):
        self.test_start_time: float = 0.0
        self.test_end_time: float = 0.0
        self.test_data: Dict[str, Any] = {}
        self.mocks: List[Any] = []
        self.temp_files: List[str] = []
        self.cleanup_callbacks: List[callable] = []

    def setup_test(self):
        """Setup method called before each test."""
        self.test_start_time = time.perf_counter()
        self.test_data = {}
        self.mocks = []
        self.temp_files = []
        self.cleanup_callbacks = []
        logger.debug(f"Setting up test: {self.__class__.__name__}")

    def teardown_test(self):
        """Teardown method called after each test."""
        # Run cleanup callbacks
        for callback in self.cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.warning(f"Cleanup callback failed: {e}")

        # Clean up temp files
        for temp_file in self.temp_files:
            try:
                import os
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                logger.warning(f"Failed to remove temp file {temp_file}: {e}")

        # Stop mocks
        for mock in self.mocks:
            try:
                mock.stop()
            except Exception as e:
                logger.warning(f"Failed to stop mock: {e}")

        self.test_end_time = time.perf_counter()
        test_duration = self.test_end_time - self.test_start_time
        logger.debug(f"Tearing down test: {self.__class__.__name__} (duration: {test_duration:.3f}s)")

    def add_cleanup_callback(self, callback: callable):
        """Add a cleanup callback to be called after the test."""
        self.cleanup_callbacks.append(callback)

    def add_temp_file(self, file_path: str):
        """Add a temporary file to be cleaned up after the test."""
        self.temp_files.append(file_path)

    def add_mock(self, mock: Any):
        """Add a mock to be stopped after the test."""
        self.mocks.append(mock)

    def set_test_data(self, key: str, value: Any):
        """Store test data for the current test."""
        self.test_data[key] = value

    def get_test_data(self, key: str, default: Any = None) -> Any:
        """Retrieve test data for the current test."""
        return self.test_data.get(key, default)

    def get_test_duration(self) -> float:
        """Get the duration of the current test in seconds."""
        if self.test_end_time > 0:
            return self.test_end_time - self.test_start_time
        return time.perf_counter() - self.test_start_time

    def run_test(self):
        """Run the actual test logic."""
        pass


class UnitTestCase(BaseTestCase, ABC):
    """
    Base class for unit tests.
    
    Unit tests should:
    - Test individual components in isolation
    - Use mocks for all external dependencies
    - Be fast and deterministic
    - Not require network or external services
    """

    def __init__(self):
        super().__init__()
        self.mock_config_manager: Optional[MockConfigurationManager] = None

    def setup_test(self):
        """Setup for unit tests."""
        super().setup_test()
        # Create mock configuration manager
        self.mock_config_manager = MockConfigurationManager()
        self.mock_config_manager.load_test_scenario("multiple_currencies")

    def create_mock_config_manager(self) -> MockConfigurationManager:
        """Create a mock configuration manager for testing."""
        config_manager = MockConfigurationManager()
        self.add_cleanup_callback(config_manager.clear)
        return config_manager

    def assert_async_raises(self, exception_type: Type[Exception]):
        """Assert that an async function raises a specific exception."""

        class AsyncExceptionContext:
            def __init__(self, test_case: UnitTestCase, exception_type: Type[Exception]):
                self.test_case = test_case
                self.exception_type = exception_type

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if exc_type is None:
                    raise AssertionError(f"Expected {self.exception_type.__name__} to be raised")
                if not issubclass(exc_type, self.exception_type):
                    raise AssertionError(f"Expected {self.exception_type.__name__}, got {exc_type.__name__}")
                return True

        return AsyncExceptionContext(self, exception_type)


class IntegrationTestCase(BaseTestCase):
    """
    Base class for integration tests.
    
    Integration tests should:
    - Test interactions between components
    - Use real or mock external services
    - Be slower than unit tests
    - Test realistic scenarios
    """
    __test__ = False  # Mark as non-test class to prevent direct collection

    def __init__(self):
        super().__init__()
        self.test_database = None

    def setup_test(self):
        """Setup for integration tests."""
        super().setup_test()
        # Setup integration test environment
        logger.debug("Setting up integration test environment")


class E2ETestCase(BaseTestCase, ABC):
    """
    Base class for end-to-end tests.
    
    E2E tests should:
    - Test complete workflows
    - Use real or near-real environments
    - Be the slowest type of test
    - Test user-facing functionality
    """

    def __init__(self):
        super().__init__()
        self.test_application = None
        self.test_client = None
        self.test_environment = None

    def setup_test_environment(self):
        """Setup the test environment for E2E tests."""
        # This would typically involve:
        # - Starting the full application
        # - Setting up test databases
        # - Configuring test services
        pass

    def cleanup_test_environment(self):
        """Cleanup the test environment after E2E tests."""
        # This would typically involve:
        # - Stopping the application
        # - Cleaning up test databases
        # - Resetting test services
        pass


# Pytest base classes
@pytest.mark.unit
class PytestUnitTestCase(UnitTestCase):
    """Base class for pytest unit tests."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Pytest fixture for setup and teardown."""
        self.setup_test()
        yield
        self.teardown_test()


@pytest.mark.integration
class PytestIntegrationTestCase(IntegrationTestCase):
    """Base class for pytest integration tests."""

    @pytest.fixture(autouse=True)
    async def setup_and_teardown(self):
        """Pytest fixture for setup and teardown."""
        self.setup_test()
        yield
        self.teardown_test()


@pytest.mark.e2e
class PytestE2ETestCase(E2ETestCase):
    """Base class for pytest end-to-end tests."""

    @pytest.fixture(autouse=True)
    async def setup_and_teardown(self):
        """Pytest fixture for setup and teardown."""
        self.setup_test()
        yield
        self.teardown_test()


# Async test utilities
class AsyncTestHelper:
    """Helper class for async testing patterns."""

    @staticmethod
    async def wait_for_condition(condition_func: callable, timeout: float = 5.0, interval: float = 0.1) -> bool:
        """
        Wait for a condition to become true.
        
        Args:
            condition_func: Function that returns True when condition is met
            timeout: Maximum time to wait in seconds
            interval: Time to wait between condition checks
            
        Returns:
            True if condition was met, False if timeout was reached
        """
        start_time = time.perf_counter()
        while time.perf_counter() - start_time < timeout:
            if await condition_func():
                return True
            await asyncio.sleep(interval)
        return False

    @staticmethod
    async def run_with_timeout(coro, timeout: float):
        """Run a coroutine with a timeout."""
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Operation timed out after {timeout} seconds")

    @staticmethod
    async def parallel_execution(tasks: List[callable], timeout: Optional[float] = None):
        """Execute multiple async tasks in parallel."""
        coroutines = [task() for task in tasks]
        if timeout:
            return await asyncio.wait_for(asyncio.gather(*coroutines), timeout=timeout)
        return await asyncio.gather(*coroutines)


# Test data builders
class TestDataBuilder:
    """Builder class for creating test data."""

    @staticmethod
    def create_transaction_data(txid: str = None, value: float = 1.0, confirmations: int = 1):
        """Create sample transaction data."""
        import random
        return {
            "txid": txid or f"tx_{random.randint(1000, 9999)}",
            "value": value,
            "confirmations": confirmations,
            "blocktime": int(time.time()),
            "vin": [{"txid": f"prev_tx_{random.randint(1000, 9999)}", "vout": 0}],
            "vout": [{"value": value, "n": 0}]
        }

    @staticmethod
    def create_utxo_data(address: str = None, value: int = 100000000, height: int = 1000):
        """Create sample UTXO data."""
        import random
        return {
            "address": address or f"bc1qtestaddress{random.randint(1000, 9999)}",
            "tx_hash": f"tx_{random.randint(1000, 9999)}",
            "tx_pos": random.randint(0, 10),
            "height": height,
            "value": value
        }

    @staticmethod
    def create_block_data(height: int = 1000, tx_count: int = 5):
        """Create sample block data."""
        return {
            "hash": f"block_hash_{height}",
            "height": height,
            "version": 536870912,
            "merkleroot": f"merkle_root_{height}",
            "time": int(time.time()),
            "tx": [f"tx_{height}_{i}" for i in range(tx_count)]
        }


# Performance testing utilities
class PerformanceTestHelper:
    """Helper class for performance testing."""

    @staticmethod
    async def measure_execution_time(coro) -> float:
        """Measure the execution time of an async function."""
        start_time = time.perf_counter()
        await coro
        end_time = time.perf_counter()
        return end_time - start_time

    @staticmethod
    async def benchmark_function(func: callable, iterations: int = 100, *args, **kwargs) -> Dict[str, float]:
        """
        Benchmark a function over multiple iterations.
        
        Returns:
            Dictionary with performance statistics
        """
        times = []
        for _ in range(iterations):
            start_time = time.perf_counter()
            await func(*args, **kwargs)
            end_time = time.perf_counter()
            times.append(end_time - start_time)

        return {
            "mean": sum(times) / len(times),
            "min": min(times),
            "max": max(times),
            "total": sum(times),
            "iterations": iterations
        }

    @staticmethod
    def assert_execution_time_under(func_result: Union[float, callable], threshold: float):
        """
        Assert that execution time is under a threshold.
        
        Args:
            func_result: Either execution time or a function to measure
            threshold: Maximum allowed execution time in seconds
        """
        if callable(func_result):
            # If it's a function, measure it
            start_time = time.perf_counter()
            result = func_result()
            execution_time = time.perf_counter() - start_time
        else:
            execution_time = func_result

        assert execution_time < threshold, f"Execution time {execution_time:.3f}s exceeds threshold {threshold}s"


# Error testing utilities
class ErrorTestHelper:
    """Helper class for testing error conditions."""

    @staticmethod
    async def assert_raises_async(exception_type: Type[Exception], coro) -> Exception:
        """
        Assert that an async function raises a specific exception.
        
        Returns:
            The raised exception
        """
        try:
            await coro
            raise AssertionError(f"Expected {exception_type.__name__} to be raised")
        except exception_type as e:
            return e
        except Exception as e:
            raise AssertionError(f"Expected {exception_type.__name__}, got {type(e).__name__}: {e}")

    @staticmethod
    def assert_error_message(error: Exception, expected_message: str):
        """Assert that an error has the expected message."""
        assert expected_message in str(error), f"Expected '{expected_message}' in error message, got: {str(error)}"

    @staticmethod
    def assert_error_code(error: Exception, expected_code: int):
        """Assert that an error has the expected code."""
        if hasattr(error, 'error_code'):
            assert error.error_code == expected_code, f"Expected error code {expected_code}, got {error.error_code}"
        else:
            raise AssertionError("Error does not have an error_code attribute")


# Mock utilities
class MockHelper:
    """Helper class for working with mocks."""

    @staticmethod
    def create_async_mock(return_value=None, side_effect=None):
        """Create an async mock."""
        mock = AsyncMock()
        if return_value is not None:
            mock.return_value = return_value
        if side_effect is not None:
            mock.side_effect = side_effect
        return mock

    @staticmethod
    def create_mock_with_methods(methods: Dict[str, Any]) -> MagicMock:
        """Create a mock with specified methods."""
        mock = MagicMock()
        for method_name, return_value in methods.items():
            if callable(return_value):
                setattr(mock, method_name, return_value)
            else:
                setattr(mock, method_name, MagicMock(return_value=return_value))
        return mock

    @staticmethod
    def verify_mock_calls(mock: MagicMock, expected_calls: List[tuple]):
        """Verify that a mock was called with expected arguments."""
        assert mock.call_count == len(expected_calls), f"Expected {len(expected_calls)} calls, got {mock.call_count}"

        for i, expected_args in enumerate(expected_calls):
            actual_call = mock.call_args_list[i]
            assert actual_call[0] == expected_args, f"Call {i}: expected {expected_args}, got {actual_call[0]}"


# Test runner utilities
class TestRunner:
    """Utility class for running tests with different configurations."""

    @staticmethod
    async def run_test_with_retries(test_func: callable, max_retries: int = 3, delay: float = 1.0, **kwargs):
        """
        Run a test with retries on failure.
        
        Args:
            test_func: The test function to run
            max_retries: Maximum number of retries
            delay: Delay between retries in seconds
            
        Returns:
            Test result or raises the last exception
        """
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(test_func):
                    return await test_func(**kwargs)
                else:
                    return test_func(**kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    logger.warning(f"Test failed on attempt {attempt + 1}, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Test failed after {max_retries + 1} attempts: {e}")

        raise last_exception

    @staticmethod
    def run_parallel_tests(test_functions: List[callable], timeout: Optional[float] = None):
        """
        Run multiple test functions in parallel.
        
        Args:
            test_functions: List of test functions to run
            timeout: Optional timeout for the parallel execution
            
        Returns:
            List of test results
        """

        async def run_tests():
            tasks = [asyncio.create_task(test()) for test in test_functions]
            if timeout:
                return await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=timeout)
            return await asyncio.gather(*tasks, return_exceptions=True)

        return asyncio.run(run_tests())
