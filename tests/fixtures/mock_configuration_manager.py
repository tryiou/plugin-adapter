"""
Mock Configuration Manager for Testing

This module provides a mock configuration manager that simulates
the behavior of the real ConfigurationManager for testing purposes.
It provides thread-safe configuration management with mock data.
"""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Union

from src.core.configuration import CoinConfig, ConfigurationManager

logger = logging.getLogger(__name__)


@dataclass
class MockCoinConfig:
    """Mock coin configuration with additional test properties."""
    host: str
    port: int
    enabled: bool = True
    timeout: int = 30
    max_retries: int = 3
    description: str = ""


class MockConfigurationManager(ConfigurationManager):
    """
    Mock configuration manager for testing.
    
    This mock provides:
    - Thread-safe configuration management
    - Configurable test scenarios
    - Configuration validation
    - Event tracking for testing
    """

    def __init__(self):
        """Initialize the mock configuration manager."""
        super().__init__()

        # Mock configuration data
        self._mock_coins: Dict[str, MockCoinConfig] = {}
        self._mock_allowed_currencies: List[str] = [
            "BTC", "LTC", "DOGE", "DASH", "BCH", "RVN", "SYS", "TZC", "XSN", "UNO", "PKOIN"
        ]

        # Test tracking
        self._load_calls = 0
        self._get_calls = 0
        self._validation_errors: List[str] = []
        self._last_error: Optional[str] = None

        # Configuration state
        self._is_loaded = False
        self._should_fail_validation = False
        self._custom_validation_rules: Dict[str, Callable] = {}

        # Event tracking
        self._events: List[Dict[str, Any]] = []

    # Override base methods

    @property
    def allowed_currencies(self) -> List[str]:
        """Get the list of allowed currencies."""
        self._track_event("get_allowed_currencies")
        return self._mock_allowed_currencies.copy()

    @property
    def coins(self) -> Dict[str, CoinConfig]:
        """Get a copy of the coins configuration."""
        with self._lock:
            self._get_calls += 1
            self._track_event("get_coins")
            return {k: CoinConfig(host=v.host, port=v.port) for k, v in self._mock_coins.items()}

    def load_from_environment(self) -> None:
        """
        Mock loading configuration from environment variables.
        
        This method simulates loading from UTXO_PLUGIN_LIST environment variable
        but uses mock data for testing purposes.
        """
        self._load_calls += 1
        self._track_event("load_from_environment")

        if self._should_fail_validation:
            self._last_error = "Simulated validation failure"
            self._validation_errors.append(self._last_error)
            return

        # Load mock configuration
        self._mock_coins = {
            "BTC": MockCoinConfig(host="localhost", port=8000, description="Bitcoin mock"),
            "LTC": MockCoinConfig(host="localhost", port=8001, description="Litecoin mock"),
            "DOGE": MockCoinConfig(host="localhost", port=8002, description="Dogecoin mock")
        }

        self._is_loaded = True
        self._track_event("configuration_loaded", {"coins": list(self._mock_coins.keys())})

    def get_coin_config(self, currency: str) -> Optional[CoinConfig]:
        """
        Get configuration for a specific currency.
        
        Args:
            currency: Currency symbol
            
        Returns:
            CoinConfig if found, None otherwise
        """
        with self._lock:
            self._get_calls += 1
            self._track_event("get_coin_config", {"currency": currency})

            if currency in self._mock_coins:
                config = self._mock_coins[currency]
                if config.enabled:
                    return CoinConfig(host=config.host, port=config.port)
                else:
                    self._track_event("coin_disabled", {"currency": currency})
                    return None
            else:
                self._track_event("coin_not_found", {"currency": currency})
                return None

    def has_currency(self, currency: str) -> bool:
        """
        Check if a currency is configured.
        
        Args:
            currency: Currency symbol
            
        Returns:
            True if currency is configured, False otherwise
        """
        with self._lock:
            self._track_event("has_currency", {"currency": currency})
            return currency in self._mock_coins and self._mock_coins[currency].enabled

    def get_all_currencies(self) -> List[str]:
        """Get list of all configured currencies."""
        with self._lock:
            self._track_event("get_all_currencies")
            return [k for k, v in self._mock_coins.items() if v.enabled]

    def clear(self) -> None:
        """Clear all configuration."""
        with self._lock:
            self._track_event("clear_configuration")
            self._mock_coins.clear()
            self._is_loaded = False
            self._load_calls = 0
            self._get_calls = 0
            self._validation_errors.clear()
            self._last_error = None

    async def close(self) -> None:
        """Close all connections and cleanup resources."""
        self._track_event("close_configuration")
        self.clear()

    # Mock-specific methods for testing

    def add_currency(self, currency: str, config: MockCoinConfig):
        """Add a currency to the mock configuration."""
        with self._lock:
            self._mock_coins[currency] = config
            self._track_event("add_currency", {"currency": currency, "config": config})

    def remove_currency(self, currency: str):
        """Remove a currency from the mock configuration."""
        with self._lock:
            if currency in self._mock_coins:
                del self._mock_coins[currency]
                self._track_event("remove_currency", {"currency": currency})

    def set_currency_enabled(self, currency: str, enabled: bool):
        """Set whether a currency is enabled."""
        with self._lock:
            if currency in self._mock_coins:
                self._mock_coins[currency].enabled = enabled
                self._track_event("set_currency_enabled", {"currency": currency, "enabled": enabled})

    def set_validation_failure(self, should_fail: bool):
        """Set whether configuration validation should fail."""
        self._should_fail_validation = should_fail

    def add_allowed_currency(self, currency: str):
        """Add a currency to the allowed list."""
        if currency not in self._mock_allowed_currencies:
            self._mock_allowed_currencies.append(currency)
            self._track_event("add_allowed_currency", {"currency": currency})

    def remove_allowed_currency(self, currency: str):
        """Remove a currency from the allowed list."""
        if currency in self._mock_allowed_currencies:
            self._mock_allowed_currencies.remove(currency)
            self._track_event("remove_allowed_currency", {"currency": currency})

    def set_mock_environment(self, plugin_list: str):
        """Set a mock UTXO_PLUGIN_LIST for testing."""
        # This would normally parse the environment variable
        # For testing, we'll just store it and use mock data
        self._track_event("set_mock_environment", {"plugin_list": plugin_list})

    # Configuration validation methods

    def validate_configuration(self) -> List[str]:
        """Validate the current configuration."""
        errors = []

        # Check if any currencies are configured
        if not self._mock_coins:
            errors.append("No currencies configured")

        # Check for duplicate hosts
        hosts = {}
        for currency, config in self._mock_coins.items():
            if config.host in hosts:
                errors.append(f"Duplicate host {config.host} for currencies {hosts[config.host]} and {currency}")
            else:
                hosts[config.host] = currency

        # Check port ranges
        for currency, config in self._mock_coins.items():
            if config.port < 1 or config.port > 65535:
                errors.append(f"Invalid port {config.port} for currency {currency}")

        # Custom validation rules
        for currency, config in self._mock_coins.items():
            if currency in self._custom_validation_rules:
                try:
                    result = self._custom_validation_rules[currency](config)
                    if result is not True:
                        errors.append(f"Custom validation failed for {currency}: {result}")
                except Exception as e:
                    errors.append(f"Custom validation error for {currency}: {str(e)}")

        self._validation_errors = errors
        return errors

    def add_custom_validation_rule(self, currency: str, rule: Callable[[MockCoinConfig], Union[bool, str]]):
        """Add a custom validation rule for a currency."""
        self._custom_validation_rules[currency] = rule

    def clear_custom_validation_rules(self):
        """Clear all custom validation rules."""
        self._custom_validation_rules.clear()

    # Test data management

    def load_test_scenario(self, scenario: str):
        """Load a predefined test scenario."""
        scenarios = {
            "single_currency": {
                "BTC": MockCoinConfig(host="localhost", port=8000, description="Single Bitcoin")
            },
            "multiple_currencies": {
                "BTC": MockCoinConfig(host="localhost", port=8000),
                "LTC": MockCoinConfig(host="localhost", port=8001),
                "DOGE": MockCoinConfig(host="localhost", port=8002)
            },
            "mixed_enabled": {
                "BTC": MockCoinConfig(host="localhost", port=8000, enabled=True),
                "LTC": MockCoinConfig(host="localhost", port=8001, enabled=False),
                "DOGE": MockCoinConfig(host="localhost", port=8002, enabled=True)
            },
            "invalid_ports": {
                "BTC": MockCoinConfig(host="localhost", port=0),  # Invalid port
                "LTC": MockCoinConfig(host="localhost", port=65536)  # Invalid port
            },
            "duplicate_hosts": {
                "BTC": MockCoinConfig(host="localhost", port=8000),
                "LTC": MockCoinConfig(host="localhost", port=8001),
                "DOGE": MockCoinConfig(host="localhost", port=8002)  # Same host, different port
            }
        }

        if scenario in scenarios:
            self._mock_coins = scenarios[scenario]
            self._track_event("load_test_scenario", {"scenario": scenario})
        else:
            raise ValueError(f"Unknown test scenario: {scenario}")

    # Statistics and tracking

    def get_stats(self) -> Dict[str, Any]:
        """Get configuration manager statistics."""
        return {
            "load_calls": self._load_calls,
            "get_calls": self._get_calls,
            "is_loaded": self._is_loaded,
            "configured_currencies": len(self._mock_coins),
            "enabled_currencies": len([c for c in self._mock_coins.values() if c.enabled]),
            "validation_errors": len(self._validation_errors),
            "last_error": self._last_error
        }

    def get_events(self) -> List[Dict[str, Any]]:
        """Get all tracked events."""
        return self._events.copy()

    def clear_events(self):
        """Clear all tracked events."""
        self._events.clear()

    def _track_event(self, event_type: str, data: Optional[Dict[str, Any]] = None):
        """Track an event for testing purposes."""
        event = {
            "type": event_type,
            "timestamp": self._get_timestamp(),
            "data": data or {}
        }
        self._events.append(event)

    def _get_timestamp(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()


class MockConfigurationFactory:
    """Factory for creating mock configurations."""

    @staticmethod
    def create_basic_config() -> MockConfigurationManager:
        """Create a basic mock configuration."""
        config = MockConfigurationManager()
        config.load_test_scenario("multiple_currencies")
        return config

    @staticmethod
    def create_single_currency_config() -> MockConfigurationManager:
        """Create a single currency configuration."""
        config = MockConfigurationManager()
        config.load_test_scenario("single_currency")
        return config

    @staticmethod
    def create_mixed_enabled_config() -> MockConfigurationManager:
        """Create a configuration with mixed enabled/disabled currencies."""
        config = MockConfigurationManager()
        config.load_test_scenario("mixed_enabled")
        return config

    @staticmethod
    def create_invalid_config() -> MockConfigurationManager:
        """Create an invalid configuration for testing error handling."""
        config = MockConfigurationManager()
        config.load_test_scenario("invalid_ports")
        return config

    @staticmethod
    def create_empty_config() -> MockConfigurationManager:
        """Create an empty configuration."""
        config = MockConfigurationManager()
        config.clear()
        return config


# Test utilities for configuration testing
class ConfigurationTestHelper:
    """Helper class for testing configuration scenarios."""

    @staticmethod
    def assert_currency_configured(config_manager: MockConfigurationManager, currency: str):
        """Assert that a currency is properly configured."""
        assert config_manager.has_currency(currency), f"Currency {currency} should be configured"
        coin_config = config_manager.get_coin_config(currency)
        assert coin_config is not None, f"Coin config for {currency} should not be None"
        assert coin_config.host, f"Host for {currency} should not be empty"
        assert coin_config.port > 0, f"Port for {currency} should be positive"

    @staticmethod
    def assert_currency_not_configured(config_manager: MockConfigurationManager, currency: str):
        """Assert that a currency is not configured."""
        assert not config_manager.has_currency(currency), f"Currency {currency} should not be configured"
        assert config_manager.get_coin_config(currency) is None, f"Coin config for {currency} should be None"

    @staticmethod
    def assert_configuration_valid(config_manager: MockConfigurationManager):
        """Assert that the configuration is valid."""
        errors = config_manager.validate_configuration()
        assert len(errors) == 0, f"Configuration should be valid, but has errors: {errors}"

    @staticmethod
    def assert_configuration_invalid(config_manager: MockConfigurationManager):
        """Assert that the configuration is invalid."""
        errors = config_manager.validate_configuration()
        assert len(errors) > 0, "Configuration should be invalid"

    @staticmethod
    def wait_for_event(config_manager: MockConfigurationManager, event_type: str, timeout: float = 5.0):
        """Wait for a specific event to occur."""
        import time
        start_time = time.time()
        while time.time() - start_time < timeout:
            events = config_manager.get_events()
            for event in events:
                if event["type"] == event_type:
                    return event
            time.sleep(0.1)
        raise TimeoutError(f"Event {event_type} did not occur within {timeout} seconds")
