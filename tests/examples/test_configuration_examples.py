"""
Configuration Testing Examples

This module provides comprehensive examples of how to test the configuration
module using the testing framework. It demonstrates best practices for
configuration testing including validation, error handling, and edge cases.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from src.core.configuration import CoinConfig, config_manager
from tests.base_test_classes import PytestUnitTestCase
from tests.fixtures.mock_configuration_manager import MockConfigurationManager
from tests.fixtures.test_data import (TestDataGenerator, TestScenario,
                                      TestScenarioFactory)


class TestConfigurationExamples(PytestUnitTestCase):
    """
    Example tests for configuration module.
    
    This class demonstrates:
    - Testing configuration loading from environment
    - Testing configuration validation
    - Testing error handling
    - Testing thread safety
    - Testing configuration persistence
    """

    def setup_test(self):
        """Setup for configuration tests."""
        super().setup_test()
        # Clear any existing configuration
        config_manager.clear()

    def test_load_from_environment_success(self):
        """Test successful loading of configuration from environment variables."""
        # Arrange
        test_env = "BTC:localhost,LTC:localhost,DOGE:localhost"

        with patch.dict(os.environ, {'UTXO_PLUGIN_LIST': test_env}):
            # Act
            config_manager.load_from_environment()

            # Assert
            assert config_manager.has_currency("BTC")
            assert config_manager.has_currency("LTC")
            assert config_manager.has_currency("DOGE")

            btc_config = config_manager.get_coin_config("BTC")
            assert btc_config.host == "localhost"
            assert btc_config.port == 8000  # Default port

    def test_load_from_environment_invalid_currency(self):
        """Test handling of invalid currencies in environment variables."""
        # Arrange
        test_env = "BTC:localhost,INVALID:localhost"

        with patch.dict(os.environ, {'UTXO_PLUGIN_LIST': test_env}):
            # Act & Assert - should not raise exception for invalid currency
            config_manager.load_from_environment()

            # BTC should be loaded, INVALID should be ignored
            assert config_manager.has_currency("BTC")
            assert not config_manager.has_currency("INVALID")

    def test_load_from_environment_missing_variable(self):
        """Test handling when UTXO_PLUGIN_LIST environment variable is missing."""
        # Arrange - ensure variable is not set
        if 'UTXO_PLUGIN_LIST' in os.environ:
            del os.environ['UTXO_PLUGIN_LIST']

        # Act & Assert - should not raise exception
        config_manager.load_from_environment()

        # Should have no currencies configured
        assert len(config_manager.get_all_currencies()) == 0

    def test_get_coin_config_existing_currency(self):
        """Test getting configuration for an existing currency."""
        # Arrange
        config_manager._coins = {
            "BTC": CoinConfig(host="localhost", port=8000)
        }

        # Act
        result = config_manager.get_coin_config("BTC")

        # Assert
        assert result is not None
        assert result.host == "localhost"
        assert result.port == 8000

    def test_get_coin_config_non_existing_currency(self):
        """Test getting configuration for a non-existing currency."""
        # Act
        result = config_manager.get_coin_config("NONEXISTENT")

        # Assert
        assert result is None

    def test_has_currency_existing(self):
        """Test checking if a currency exists."""
        # Arrange
        config_manager._coins = {
            "BTC": CoinConfig(host="localhost", port=8000)
        }

        # Act
        result = config_manager.has_currency("BTC")

        # Assert
        assert result is True

    def test_has_currency_non_existing(self):
        """Test checking if a non-existing currency exists."""
        # Act
        result = config_manager.has_currency("NONEXISTENT")

        # Assert
        assert result is False

    def test_get_all_currencies(self):
        """Test getting all configured currencies."""
        # Arrange
        config_manager._coins = {
            "BTC": CoinConfig(host="localhost", port=8000),
            "LTC": CoinConfig(host="localhost", port=8001)
        }

        # Act
        result = config_manager.get_all_currencies()

        # Assert
        assert "BTC" in result
        assert "LTC" in result
        assert len(result) == 2

    def test_clear_configuration(self):
        """Test clearing all configuration."""
        # Arrange
        config_manager._coins = {
            "BTC": CoinConfig(host="localhost", port=8000)
        }
        config_manager._hashx_cache["test"] = "value"

        # Act
        config_manager.clear()

        # Assert
        assert len(config_manager._coins) == 0
        assert len(config_manager._hashx_cache) == 0

    @pytest.mark.asyncio
    async def test_async_configuration_access(self):
        """Test async-safe configuration access."""
        # Arrange
        config_manager._coins = {
            "BTC": CoinConfig(host="localhost", port=8000)
        }

        # Act
        async_result = await config_manager.get_coins_async()
        sync_result = config_manager.coins

        # Assert
        assert async_result == sync_result
        assert "BTC" in async_result

    def test_thread_safety(self):
        """Test that configuration manager is thread-safe."""
        import threading
        import time

        # Arrange
        results = []
        errors = []

        def add_currency(thread_id):
            try:
                for i in range(10):
                    currency = f"CURRENCY_{thread_id}_{i}"
                    config_manager._coins[currency] = CoinConfig(
                        host=f"host_{thread_id}",
                        port=8000 + thread_id
                    )
                    time.sleep(0.001)  # Small delay to increase chance of race condition
                results.append(thread_id)
            except Exception as e:
                errors.append(e)

        # Act - Run multiple threads concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=add_currency, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Assert
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5, f"Expected 5 threads to complete, got {len(results)}"
        assert len(config_manager._coins) == 50, f"Expected 50 currencies, got {len(config_manager._coins)}"

    def test_update_hashx_cache(self):
        """Test updating the hashx cache."""
        # Arrange
        test_key = "test_key"
        test_value = {"some": "data"}

        # Act
        config_manager.update_hashx_cache(test_key, test_value)

        # Assert
        assert config_manager.get_hashx_cache_value(test_key) == test_value

    def test_get_hashx_cache_value_existing(self):
        """Test getting a value from hashx cache that exists."""
        # Arrange
        test_key = "test_key"
        test_value = {"some": "data"}
        config_manager._hashx_cache[test_key] = test_value

        # Act
        result = config_manager.get_hashx_cache_value(test_key)

        # Assert
        assert result == test_value

    def test_get_hashx_cache_value_non_existing(self):
        """Test getting a value from hashx cache that doesn't exist."""
        # Act
        result = config_manager.get_hashx_cache_value("non_existing_key")

        # Assert
        assert result is None


class TestMockConfigurationManagerExamples(PytestUnitTestCase):
    """
    Example tests using the MockConfigurationManager.
    
    This class demonstrates how to use the mock configuration manager
    for more controlled testing scenarios.
    """

    def setup_test(self):
        """Setup for mock configuration tests."""
        super().setup_test()
        self.mock_config = MockConfigurationManager()

    def test_mock_configuration_basic_usage(self):
        """Test basic usage of mock configuration manager."""
        # Arrange
        self.mock_config.load_test_scenario("multiple_currencies")

        # Act
        currencies = self.mock_config.get_all_currencies()
        btc_config = self.mock_config.get_coin_config("BTC")

        # Assert
        assert "BTC" in currencies
        assert "LTC" in currencies
        assert "DOGE" in currencies
        assert btc_config is not None
        assert btc_config.host == "localhost"
        assert btc_config.port == 8000

    def test_mock_configuration_validation(self):
        """Test configuration validation with mock."""
        # Arrange
        self.mock_config.load_test_scenario("invalid_ports")

        # Act
        errors = self.mock_config.validate_configuration()

        # Assert
        assert len(errors) > 0
        assert any("Invalid port" in error for error in errors)

    def test_mock_configuration_custom_validation(self):
        """Test custom validation rules with mock."""
        # Arrange
        self.mock_config.add_currency("BTC", MagicMock(host="localhost", port=8000))

        def custom_rule(config):
            if config.host == "localhost":
                return True
            return "Host must be localhost"

        self.mock_config.add_custom_validation_rule("BTC", custom_rule)

        # Act
        errors = self.mock_config.validate_configuration()

        # Assert
        assert len(errors) == 0

    def test_mock_configuration_disabled_currency(self):
        """Test handling of disabled currencies."""
        # Arrange
        self.mock_config.load_test_scenario("mixed_enabled")

        # Act
        all_currencies = self.mock_config._mock_coins.keys()
        enabled_currencies = self.mock_config.get_all_currencies()
        btc_has = self.mock_config.has_currency("BTC")
        ltc_has = self.mock_config.has_currency("LTC")

        # Assert
        assert len(all_currencies) == 3  # BTC, LTC, DOGE
        assert len(enabled_currencies) == 2  # BTC, DOGE (LTC is disabled)
        assert btc_has is True
        assert ltc_has is False

    def test_mock_configuration_events(self):
        """Test event tracking in mock configuration."""
        # Arrange
        self.mock_config.clear_events()

        # Act
        self.mock_config.load_from_environment()
        self.mock_config.get_coin_config("BTC")

        # Assert
        events = self.mock_config.get_events()
        assert len(events) >= 2
        assert any(event["type"] == "load_from_environment" for event in events)
        assert any(event["type"] == "get_coin_config" for event in events)


class TestConfigurationIntegrationExamples(PytestUnitTestCase):
    """
    Example integration tests for configuration.
    
    This class demonstrates integration testing patterns for configuration.
    """

    def test_configuration_with_application(self):
        """Test configuration working with application components."""
        # This would test how configuration integrates with the application
        # For now, just a placeholder for integration test patterns
        pass

    def test_configuration_persistence(self):
        """Test configuration persistence across application restarts."""
        # This would test configuration file loading/saving
        # For now, just a placeholder for persistence test patterns
        pass


# Test data builders and factories examples
class TestConfigurationDataBuilders(PytestUnitTestCase):
    """
    Example tests for configuration data builders.
    """

    def test_data_generator_basic(self):
        """Test basic data generation."""
        # Arrange
        generator = TestDataGenerator()

        # Act
        currency = generator.generate_currency("BTC")
        address = generator.generate_address("BTC")
        utxo = generator.generate_utxo()

        # Assert
        assert currency.symbol == "BTC"
        assert currency.host == "localhost"
        assert address.currency == "BTC"
        assert utxo.currency == "BTC"
        assert utxo.value > 0

    def test_scenario_factory(self):
        """Test scenario factory."""
        # Test single currency scenario
        scenario = TestScenarioFactory.create_single_currency_scenario()
        assert "currencies" in scenario.data
        assert "BTC" in scenario.data["currencies"]

        # Test multi currency scenario
        scenario = TestScenarioFactory.create_multi_currency_scenario()
        assert len(scenario.data["currencies"]) == 3
        assert "BTC" in scenario.data["currencies"]
        assert "LTC" in scenario.data["currencies"]
        assert "DOGE" in scenario.data["currencies"]

    def test_scenario_setup_and_cleanup(self):
        """Test scenario setup and cleanup."""
        # Arrange
        scenario = TestScenario("test_scenario", "Test scenario")

        setup_called = False
        cleanup_called = False

        async def setup_func():
            nonlocal setup_called
            setup_called = True

        async def cleanup_func():
            nonlocal cleanup_called
            cleanup_called = True

        scenario.add_setup_step(setup_func)
        scenario.add_cleanup_step(cleanup_func)

        # Act
        import asyncio
        asyncio.run(scenario.setup())
        asyncio.run(scenario.cleanup())

        # Assert
        assert setup_called is True
        assert cleanup_called is True


# Performance testing examples
class TestConfigurationPerformanceExamples(PytestUnitTestCase):
    """
    Example performance tests for configuration.
    """

    @pytest.mark.performance
    def test_configuration_load_performance(self):
        """Test configuration loading performance."""
        # Arrange
        import time
        generator = TestDataGenerator()

        # Act
        start_time = time.perf_counter()

        # Load a large configuration
        for _ in range(100):
            currency = generator.generate_currency()
            # Simulate loading

        end_time = time.perf_counter()
        load_time = end_time - start_time

        # Assert
        assert load_time < 1.0, f"Configuration loading took too long: {load_time:.3f}s"

    @pytest.mark.performance
    def test_configuration_access_performance(self):
        """Test configuration access performance."""
        # Arrange
        config_manager._coins = {
            f"CURRENCY_{i}": CoinConfig(host=f"host_{i}", port=8000 + i)
            for i in range(1000)
        }

        # Act
        import time
        start_time = time.perf_counter()

        # Access configurations multiple times
        for _ in range(1000):
            config_manager.get_coin_config("CURRENCY_500")

        end_time = time.perf_counter()
        access_time = end_time - start_time

        # Assert
        assert access_time < 0.1, f"Configuration access took too long: {access_time:.3f}s"


# Error testing examples
class TestConfigurationErrorExamples(PytestUnitTestCase):
    """
    Example error handling tests for configuration.
    """

    def test_configuration_error_handling(self):
        """Test handling of configuration errors."""
        # Test various error scenarios
        pass

    def test_configuration_recovery(self):
        """Test recovery from configuration errors."""
        # Test recovery patterns
        pass


# Documentation examples
"""
Configuration Testing Best Practices:

1. **Environment Isolation**:
   - Always clear configuration between tests
   - Use mock configurations for controlled testing
   - Don't rely on real environment variables in tests

2. **Thread Safety Testing**:
   - Test concurrent access to configuration
   - Verify locks work correctly
   - Test race conditions

3. **Error Handling**:
   - Test invalid configurations
   - Test missing environment variables
   - Test recovery from errors

4. **Performance Testing**:
   - Test configuration loading with large datasets
   - Test concurrent access performance
   - Test memory usage

5. **Integration Testing**:
   - Test configuration with real application components
   - Test configuration persistence
   - Test configuration updates

6. **Mock Usage**:
   - Use MockConfigurationManager for controlled testing
   - Test edge cases with mock data
   - Verify mock behavior matches real implementation
"""
