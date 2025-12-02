#!/usr/bin/env python3
"""
Unit tests for ConfigurationManager.
Tests cover basic functionality and configuration loading.
"""

import os
from unittest.mock import patch

from src.core.configuration import CoinConfig, ConfigurationManager


class TestConfigurationManager:
    """Test suite for ConfigurationManager class."""

    def setup_method(self):
        """Setup for each test method."""
        self.config_manager = ConfigurationManager()
        self.config_manager.clear()

    def teardown_method(self):
        """Cleanup after each test method."""
        self.config_manager.clear()

    def test_initialization(self):
        """Test ConfigurationManager initialization."""
        assert isinstance(self.config_manager._coins, dict)
        assert isinstance(self.config_manager._hashx_cache, dict)
        assert len(self.config_manager._coins) == 0
        assert len(self.config_manager._hashx_cache) == 0

    def test_load_from_environment_success(self):
        """Test successful loading from environment variables."""
        test_env = "BTC:localhost,LTC:localhost"

        with patch.dict(os.environ, {'UTXO_PLUGIN_LIST': test_env}):
            self.config_manager.load_from_environment()

        assert self.config_manager.has_currency("BTC")
        assert self.config_manager.has_currency("LTC")

        btc_config = self.config_manager.get_coin_config("BTC")
        assert btc_config.host == "localhost"
        assert btc_config.port == 8000

    def test_get_coin_config_existing(self):
        """Test getting configuration for existing currency."""
        self.config_manager._coins["BTC"] = CoinConfig(host="localhost", port=8000)

        config = self.config_manager.get_coin_config("BTC")
        assert config is not None
        assert config.host == "localhost"
        assert config.port == 8000

    def test_has_currency_existing(self):
        """Test checking for existing currency."""
        self.config_manager._coins["BTC"] = CoinConfig(host="localhost", port=8000)
        assert self.config_manager.has_currency("BTC") is True

    def test_update_hashx_cache(self):
        """Test updating hashx cache."""
        self.config_manager.update_hashx_cache("key1", "value1")
        value = self.config_manager.get_hashx_cache_value("key1")
        assert value == "value1"

    def test_clear(self):
        """Test clearing all configuration."""
        self.config_manager._coins["BTC"] = CoinConfig(host="localhost", port=8000)
        self.config_manager._hashx_cache["test"] = "value"

        self.config_manager.clear()

        assert len(self.config_manager.coins) == 0
        assert len(self.config_manager.hashx_cache) == 0

    def test_coin_config_dataclass(self):
        """Test CoinConfig dataclass functionality."""
        config = CoinConfig(host="testhost", port=8080)

        assert config.host == "testhost"
        assert config.port == 8080

        # Test equality
        config2 = CoinConfig(host="testhost", port=8080)
        assert config == config2
