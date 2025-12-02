#!/usr/bin/env python3

import logging
import os
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.core.constants import ConfigConstants
from src.utils.operation_logger import OperationLogger

logger = logging.getLogger(__name__)


@dataclass
class CoinConfig:
    """Configuration for a single cryptocurrency."""
    host: str
    port: int


class ConfigurationManager:
    """
    Thread-safe configuration manager that replaces global state.
    Handles cryptocurrency configurations and socket management.
    """

    def __init__(self):
        """Initialize the configuration manager with thread-safe data structures."""
        self._coins: Dict[str, CoinConfig] = {}
        self._allowed_currencies: List[str] = [
            "BLOCK", "BTC", "BCH", "LTC", "DASH", "DOGE", "DGB", "PIVX", "RVN",
            "SYS", "TZC", "XSN", "UNO", "PKOIN"
        ]
        self._hashx_cache: Dict[str, Any] = {}
        self._lock = threading.RLock()  # Reentrant lock for both sync and async

    @property
    def allowed_currencies(self) -> List[str]:
        """Get the list of allowed currencies."""
        return self._allowed_currencies.copy()

    @property
    def coins(self) -> Dict[str, CoinConfig]:
        """Get a copy of the coins configuration."""
        with self._lock:
            return {k: v for k, v in self._coins.items()}

    @property
    def hashx_cache(self) -> Dict[str, Any]:
        """Get the hashx cache."""
        with self._lock:
            return self._hashx_cache.copy()

    async def get_coins_async(self) -> Dict[str, CoinConfig]:
        """Async-safe method to get coins configuration."""
        with self._lock:
            return {k: v for k, v in self._coins.items()}

    async def get_hashx_cache_async(self) -> Dict[str, Any]:
        """Async-safe method to get hashx cache."""
        with self._lock:
            return self._hashx_cache.copy()

    def load_from_environment(self) -> None:
        """
        Load cryptocurrency configurations from environment variables.
        
        Expects UTXO_PLUGIN_LIST environment variable in format:
        "CURRENCY1:HOST1,CURRENCY2:HOST2,..."
        """
        start = OperationLogger.start("load_from_environment", "system")
        utxo_plugins = os.environ.get('UTXO_PLUGIN_LIST')
        if not utxo_plugins:
            OperationLogger.error("load_from_environment", "system",
                                  Exception("UTXO_PLUGIN_LIST environment variable not set"))
            OperationLogger.end("load_from_environment", start, "system")
            return

        with self._lock:
            for utxo_plugin in utxo_plugins.split(","):
                try:
                    currency, host = utxo_plugin.split(":")
                    currency = currency.strip()
                    host = host.strip()

                    if currency not in self._allowed_currencies:
                        OperationLogger.error("load_from_environment", currency,
                                              Exception(f"Unsupported currency: {currency}"))
                        continue

                    self._coins[currency] = CoinConfig(host=host, port=ConfigConstants.DEFAULT_ELECTRUM_PORT)
                    # No need to log success for each currency - just count them

                except ValueError as e:
                    OperationLogger.error("load_from_environment", "system", e)

        OperationLogger.end("load_from_environment", start, "system")

    def get_coin_config(self, currency: str) -> Optional[CoinConfig]:
        """
        Get configuration for a specific currency.
        
        Args:
            currency: Currency symbol (e.g., "BTC", "LTC")
            
        Returns:
            CoinConfig if found, None otherwise
        """
        with self._lock:
            return self._coins.get(currency)

    def has_currency(self, currency: str) -> bool:
        """
        Check if a currency is configured.
        
        Args:
            currency: Currency symbol
            
        Returns:
            True if currency is configured, False otherwise
        """
        with self._lock:
            return currency in self._coins

    def get_all_currencies(self) -> List[str]:
        """Get list of all configured currencies."""
        with self._lock:
            return list(self._coins.keys())

    def clear(self) -> None:
        """Clear all configuration (for testing purposes)."""
        with self._lock:
            self._coins.clear()
            self._hashx_cache.clear()

    def update_hashx_cache(self, key: str, value: Any) -> None:
        """Update the hashx cache with a new value."""
        with self._lock:
            self._hashx_cache[key] = value

    def get_hashx_cache_value(self, key: str) -> Optional[Any]:
        """Get a value from the hashx cache."""
        with self._lock:
            return self._hashx_cache.get(key)

    async def close(self) -> None:
        """Close all connections and cleanup resources."""
        # start = OperationLogger.start("close", "system")
        with self._lock:
            # Clear all references to help garbage collection
            self._coins.clear()
            self._hashx_cache.clear()

        # OperationLogger.end("close", start, "system")


# Global configuration manager instance - this replaces the global 'coins' variable
# but is now thread-safe and encapsulated
config_manager = ConfigurationManager()
