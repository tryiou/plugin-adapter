#!/usr/bin/env python3

import logging
import os
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class CoinConfig:
    """Configuration for a single cryptocurrency."""
    host: str
    port: int
    socket: Optional['TCPSocket'] = None


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
        self._lock = Lock()

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

    def load_from_environment(self) -> None:
        """
        Load cryptocurrency configurations from environment variables.
        
        Expects UTXO_PLUGIN_LIST environment variable in format:
        "CURRENCY1:HOST1,CURRENCY2:HOST2,..."
        """
        utxo_plugins = os.environ.get('UTXO_PLUGIN_LIST')
        if not utxo_plugins:
            logger.warning("[config] UTXO_PLUGIN_LIST environment variable not set")
            return

        with self._lock:
            for utxo_plugin in utxo_plugins.split(","):
                try:
                    currency, host = utxo_plugin.split(":")
                    currency = currency.strip()
                    host = host.strip()

                    if currency not in self._allowed_currencies:
                        logger.warning(f"[config] Skipping unsupported currency: {currency}")
                        continue

                    self._coins[currency] = CoinConfig(host=host, port=8000)
                    logger.info(f"[config] Loaded configuration for {currency}: {host}:8000")

                except ValueError as e:
                    logger.error(f"[config] Invalid UTXO_PLUGIN_LIST format for: {utxo_plugin} - {e}")

        logger.info(f'[config] ACTIVE UTXOPLUGINS:\n{self._coins}')

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

    def set_coin_socket(self, currency: str, socket: 'TCPSocket') -> bool:
        """
        Set the socket connection for a currency.
        
        Args:
            currency: Currency symbol
            socket: TCPSocket instance
            
        Returns:
            True if successful, False if currency not found
        """
        with self._lock:
            if currency in self._coins:
                old_socket = self._coins[currency].socket
                self._coins[currency].socket = socket
                
                # Log socket state changes for debugging
                old_state = "None" if old_socket is None else f"Connected: {old_socket.is_connected}"
                new_state = "None" if socket is None else f"Connected: {socket.is_connected}"
                logger.info(f"[config] {currency} - Socket updated. Old: {old_state}, New: {new_state}")
                
                return True
            logger.warning(f"[config] Attempted to set socket for unknown currency: {currency}")
            return False

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


# Global configuration manager instance - this replaces the global 'coins' variable
# but is now thread-safe and encapsulated
config_manager = ConfigurationManager()
