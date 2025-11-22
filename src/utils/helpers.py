#!/usr/bin/env python3

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from decimal import Decimal

from aiorpcx import connect_rs, timeout_after
from src.core.error_handling import NetworkError, ProtocolError
from src.core.configuration import config_manager

logger = logging.getLogger(__name__)


async def get_info(currency: str, initial: bool = False) -> Optional[Dict[str, Any]]:
    """
    Get server info for a specific currency.
    
    Args:
        currency: Currency symbol
        initial: Whether this is an initial connection check
        
    Returns:
        Server info dictionary or None if failed
    """
    if not config_manager.has_currency(currency):
        print(f"[client] ERROR: Attempted to get info for unsupported coin {currency}")
        return None

    coin_config = config_manager.get_coin_config(currency)
    if not coin_config:
        return None
        
    host = coin_config.host
    port = coin_config.port

    result = None

    async def send_request():
        try:
            async with timeout_after(15):
                async with connect_rs(host, port) as session:
                    session.transport._framer.max_size = 0
                    nonlocal result
                    result = await session.send_request("getinfo")

                    if initial:
                        print(f"[heartbeat] Initial heartbeat for {currency}:")
                        print(f"\tPID: {str(result['pid'])}")
                        print(f"\tServer version: {result['version']}")
                    else:
                        print(f"[heartbeat] {currency}: ")
                        print(f"\tHeight (DB/Daemon): {str(result['db_height'])} / {str(result['daemon_height'])} blocks")
                        print(f"\tuptime {result['uptime']}")

                    return result
        except Exception as e:
            if initial:
                print(f"[heartbeat] Failed to get info for {currency} during initial setup: {e}")
            else:
                print(f"[heartbeat] Failed to get info for {currency}: {e}")
            return None
    
    return await send_request()


async def get_block_count(currency: str) -> Optional[int]:
    """
    Get block count for a currency.
    
    Args:
        currency: Currency symbol
        
    Returns:
        Block count or None if failed
    """
    if not config_manager.has_currency(currency):
        logger.warning(f"[client] ERROR: Attempted to get info for unsupported coin {currency}")
        return None

    coin_config = config_manager.get_coin_config(currency)
    if not coin_config or not coin_config.socket:
        return None
        
    socket = coin_config.socket
    start_time = time.time()
    
    try:
        res = await socket.send_message("getblockcount", (), timeout=2)
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"[client] Execution time for 'get_block_count' {currency}: {execution_time} seconds")
        
        if res in [-1, -2]:  # OS_ERROR or OTHER_EXCEPTION
            return None
        return res
    except Exception as e:
        logger.error(f"[client] Error getting block count for {currency}: {e}")
        return None


async def get_plugin_fees(currency: str) -> Optional[float]:
    """
    Get relay fee for a currency.
    
    Args:
        currency: Currency symbol
        
    Returns:
        Relay fee or None if failed
    """
    if not config_manager.has_currency(currency):
        logger.warning(f"[client] ERROR: Attempted to get info for unsupported coin {currency}")
        return None

    coin_config = config_manager.get_coin_config(currency)
    if not coin_config or not coin_config.socket:
        return None
        
    socket = coin_config.socket

    try:
        res = await socket.send_message("blockchain.relayfee", (), timeout=2)

        if res in [-1, -2]:  # OS_ERROR or OTHER_EXCEPTION
            return None
        return res
    except Exception as e:
        logger.error(f"[client] Error getting plugin fees for {currency}: {e}")
        return None


def create_plugin_block_heights_response(heights: Dict[str, Optional[int]]) -> str:
    """
    Create standardized response for plugin block heights endpoint.
    
    Args:
        heights: Dictionary mapping currencies to their heights
        
    Returns:
        JSON string response
    """
    import json
    res = {'result': heights, 'error': None}
    logger.info(f"[server] plugin_block_heights() {res}")
    return json.dumps(res)


def create_plugin_tx_fees_response(fees: Dict[str, Optional[Decimal]]) -> str:
    """
    Create standardized response for plugin transaction fees endpoint.
    
    Args:
        fees: Dictionary mapping currencies to their fees
        
    Returns:
        JSON string response
    """
    import simplejson
    res = {'result': fees, 'error': None}
    logger.info(f"[server] plugin_tx_fees() {res}")
    return simplejson.dumps(res)


def validate_address_list(addresses: Any) -> List[str]:
    """
    Validate and normalize address list from various input formats.
    
    Args:
        addresses: Raw address input (string, list, or JSON string)
        
    Returns:
        List of validated addresses
        
    Raises:
        ValueError: If addresses cannot be parsed or are invalid
    """
    if not addresses:
        raise ValueError("No addresses provided")
    
    # Handle JSON string input
    if isinstance(addresses, str):
        try:
            addresses = json.loads(addresses)
        except json.JSONDecodeError:
            # If not valid JSON, treat as comma-separated string
            addresses = addresses.split(',')
    
    # Validate list format
    if not isinstance(addresses, list):
        raise ValueError("Addresses must be provided as a list or comma-separated string")
    
    # Clean and validate individual addresses
    cleaned_addresses = []
    for addr in addresses:
        if isinstance(addr, str) and addr.strip():
            cleaned_addresses.append(addr.strip())
    
    if not cleaned_addresses:
        raise ValueError("No valid addresses found")
    
    return cleaned_addresses


def format_utxo_output(utxos: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Format UTXO data for API response.
    
    Args:
        utxos: List of UTXO dictionaries
        
    Returns:
        Formatted response dictionary
    """
    return {"utxos": utxos}


def format_balance_output(balance_data: Dict[str, int]) -> Dict[str, Any]:
    """
    Format balance data for API response.
    
    Args:
        balance_data: Raw balance data from ElectrumX
        
    Returns:
        Formatted balance response
    """
    result = balance_data.copy()
    
    if result['confirmed'] > 0:
        result['confirmed'] = float(result['confirmed']) / 100000000.0

    if result['unconfirmed'] > 0:
        result['unconfirmed'] = float(result['unconfirmed']) / 100000000.0
    
    return result