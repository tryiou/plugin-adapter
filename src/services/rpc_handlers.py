#!/usr/bin/env python3

import asyncio
import json
import logging
import time
import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from json import JSONDecodeError

from src.core.error_handling import (
    NetworkError, ProtocolError, TransactionError, ValidationError,
    create_error_response, create_success_response
)
from src.core.configuration import config_manager

logger = logging.getLogger(__name__)


def TimestampMillisec64() -> int:
    """Get current timestamp in milliseconds since Unix epoch."""
    return int((datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)).total_seconds() * 1000)


def parse_response(response: List[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
    """
    Parse UTXO response data into standardized format.
    
    Args:
        response: Raw response from ElectrumX server
        
    Returns:
        Parsed UTXO data or None if parsing fails
    """
    refined_result = []
    
    logger.debug(f"[server] response: {str(response)}")
    try:
        for utxos in response:
            for item in utxos:
                refined_result.append({
                    "address": item['address'],
                    "txhash": item['tx_hash'],
                    "vout": int(item['tx_pos']),
                    "block_number": int(item['height']),
                    "value": float(item['value']) / 100000000.0
                })
        
        return refined_result
    except (TypeError, KeyError, ValueError) as e:
        logger.info(f"[ERROR] Error parsing response: {str(e)}")
        return None


class BaseRPCHandler:
    """Base class for all RPC handlers providing common functionality."""
    
    def _validate_currency(self, currency: str) -> bool:
        """
        Validate that a currency is supported and configured.
        
        Args:
            currency: Currency symbol to validate
            
        Returns:
            True if currency is valid, raises exception otherwise
        """
        if not config_manager.has_currency(currency):
            logger.warning(f"[client] ERROR: Attempted to get UTXOs from unsupported coin {currency}")
            return False
        return True
    
    def _get_socket(self, currency: str):
        """Get the socket connection for a currency."""
        coin_config = config_manager.get_coin_config(currency)
        if not coin_config or not coin_config.socket:
            raise NetworkError(f"No socket connection available for {currency}")
        return coin_config.socket


class UTXORPCHandler(BaseRPCHandler):
    """Handler for UTXO-related RPC methods."""
    
    async def getutxos(self, params: List[Any]) -> str:
        """
        Get UTXOs for specified addresses.
        
        Args:
            params: [currency, addresses]
            
        Returns:
            JSON string with UTXO data
        """
        currency = params[0]
        if not self._validate_currency(currency):
            return json.dumps([])
        
        # Parse addresses
        try:
            addresses = json.loads(params[1])
        except (TypeError, JSONDecodeError):
            addresses = params[1]
        
        if isinstance(addresses, str):
            addresses = addresses.split(',')
        
        if not addresses or not isinstance(addresses, list):
            return json.dumps([])
        
        timestart = TimestampMillisec64()
        logger.info(f"[server] {timestart} xrmgetutxos: {currency}")
        
        socket = self._get_socket(currency)
        
        try:
            data = await socket.send_batch("blockchain.address.listunspent", addresses, timeout=30)
            
            if data in [-1, -2]:  # OS_ERROR or OTHER_EXCEPTION
                logging.info(f"[server] getutxos failed for coin: {currency}")
                return json.dumps([])
            
            res = {"utxos": parse_response(data)}
            
            if res is None or res['utxos'] is None:
                logging.info(f"[server] getutxos failed for coin: {currency}")
                return json.dumps([])
            
            logger.debug(f"DEBUG MESSAGE: {str(res)}")
            logger.info(f"[server-end getutxos] completion time: {TimestampMillisec64() - timestart}ms")
            
            return json.dumps(res)
            
        except (NetworkError, ProtocolError) as e:
            return json.dumps(create_error_response(e))


class TransactionRPCHandler(BaseRPCHandler):
    """Handler for transaction-related RPC methods."""
    
    async def getrawtransaction(self, params: List[Any]) -> str:
        """
        Get raw transaction data.
        
        Args:
            params: [currency, txid, verbose?]
            
        Returns:
            JSON string with transaction data
        """
        currency = params[0]
        txid = params[1]
        verbose = False
        
        if len(params) == 3:
            v = params[2]
            if any(x == v for x in [True, 'true', 'True', '1', 1]):
                verbose = True
        
        logger.info(f"[server] xrmgetrawtransaction: {currency} - {str(txid)}")
        
        if not self._validate_currency(currency):
            return json.dumps(create_error_response(ProtocolError("Unsupported currency")))
        
        socket = self._get_socket(currency)
        res = {'result': None, 'error': None}
        
        try:
            data = await socket.send_message("blockchain.transaction.get", [txid, verbose], timeout=30)
            
            if data in [-1, -2]:  # OS_ERROR or OTHER_EXCEPTION
                logger.error("[server] ERROR: Error during getrawtranscation grabbing!")
                res['error'] = -5
            else:
                res['result'] = data
                
        except Exception as e:
            logger.error(f"[server] ERROR: Error during getrawtranscation grabbing! {str(e)}")
            res['error'] = -5
        
        logger.debug(f"DEBUG MESSAGE: {str(res)}")
        return json.dumps(res)
    
    async def getrawmempool(self, params: List[Any]) -> str:
        """
        Get raw mempool data.
        
        Args:
            params: [currency, verbose?]
            
        Returns:
            JSON string with mempool data
        """
        currency = params[0]
        verbose = False
        
        if len(params) == 2:
            v = params[1]
            if any(x == v for x in [True, 'true', 'True', '1', 1]):
                verbose = True
        
        logger.info(f"[server] xrmgetrawmempool: {currency} - {str(verbose)}")
        
        if not self._validate_currency(currency):
            return json.dumps(create_error_response(ProtocolError("Unsupported currency")))
        
        socket = self._get_socket(currency)
        res = {'result': None, 'error': None}
        
        try:
            data = await socket.send_message("getrawmempool", [verbose], timeout=30)
            
            if data in [-1, -2]:  # OS_ERROR or OTHER_EXCEPTION
                logger.error("[server] ERROR: Error during getrawmempool grabbing!")
                res['error'] = -1
            else:
                res['result'] = data
                
        except Exception as e:
            logger.error(f"[server] ERROR: Error during getrawmempool grabbing! {str(e)}")
            res['error'] = -1
        
        logger.debug(f"DEBUG MESSAGE: {str(res)}")
        return json.dumps(res)
    
    async def sendrawtransaction(self, params: List[Any]) -> str:
        """
        Broadcast a raw transaction.
        
        Args:
            params: [currency, rawtx]
            
        Returns:
            JSON string with transaction ID or error
        """
        currency = params[0]
        rawtx = params[1]
        
        logger.info(f"[server] xrmsendrawtransaction: {currency}")
        
        if not self._validate_currency(currency):
            return json.dumps(create_error_response(ProtocolError("Unsupported currency")))
        
        socket = self._get_socket(currency)
        res = {'result': None, 'error': None}
        
        try:
            data = await socket.send_message("blockchain.transaction.broadcast", [rawtx], timeout=30)
            
            if data == -1:  # OS_ERROR
                logger.error("[server] ERROR: OSError during sendrawtransaction!")
                res['error'] = -1
            elif data == -2:  # OTHER_EXCEPTION
                logger.error("[server] ERROR: -25 during sendrawtransaction!")
                res['error'] = -25
            else:
                res['result'] = data
                
        except Exception as e:
            logger.error(f"[server] ERROR: Error during sendrawtransaction! {str(e)}")
            res['error'] = -25
        
        logger.debug(f"DEBUG MESSAGE: {str(res)}")
        return json.dumps(res)
    
    async def gettransaction(self, params: List[Any]) -> str:
        """
        Get transaction details.
        
        Args:
            params: [currency, txid]
            
        Returns:
            JSON string with transaction data
        """
        currency = params[0]
        txid = params[1]
        verbose = True
        
        logger.info(f"[server] xrmgettransaction: {currency} - {str(txid)}")
        
        if not self._validate_currency(currency):
            return json.dumps(create_error_response(ProtocolError("Unsupported currency")))
        
        socket = self._get_socket(currency)
        res = {'result': None, 'error': None}
        
        try:
            data = await socket.send_message("blockchain.transaction.get", [txid, verbose], timeout=30)
            
            if data in [-1, -2]:  # OS_ERROR or OTHER_EXCEPTION
                logger.error("[server] ERROR: Error during getblock grabbing!")
                res['error'] = -1
            else:
                res['result'] = data
                
        except Exception as e:
            logger.error(f"[server] ERROR: Error during gettransaction grabbing! {str(e)}")
            res['error'] = -1
        
        logger.debug(f"DEBUG MESSAGE: {str(res)}")
        return json.dumps(res)


class BlockRPCHandler(BaseRPCHandler):
    """Handler for block-related RPC methods."""
    
    async def getblockcount(self, params: List[Any]) -> str:
        """
        Get current block count.
        
        Args:
            params: [currency]
            
        Returns:
            JSON string with block count
        """
        currency = params[0]
        logger.info(f"[server] xrmgetblockcount: {currency}")
        
        if not self._validate_currency(currency):
            return json.dumps(create_error_response(ProtocolError("Unsupported currency")))
        
        socket = self._get_socket(currency)
        res = {'result': None, 'error': None}
        
        try:
            data = await socket.send_message("getblockcount", (), timeout=2)
            
            if data in [-1, -2]:  # OS_ERROR or OTHER_EXCEPTION
                logger.error("[server] ERROR: Error during getblockcount grabbing!")
                res['error'] = -1
            else:
                res['result'] = data
                
        except Exception as e:
            logger.error(f"[server] ERROR: Error during getblockcount grabbing! {str(e)}")
            res['error'] = -1
        
        logger.debug(f"DEBUG MESSAGE: {str(res)}")
        return json.dumps(res)
    
    async def getblock(self, params: List[Any]) -> str:
        """
        Get block data by hash.
        
        Args:
            params: [currency, hex_hash, verbose?]
            
        Returns:
            JSON string with block data
        """
        currency = params[0]
        hex_hash = params[1]
        verbose = False
        
        if len(params) == 3:
            v = params[2]
            if any(x == v for x in [True, 'true', 'True', '1', 1]):
                verbose = True
        
        logger.info(f"[server] xrmgetblock: {currency} - {str(hex_hash)}")
        
        if not self._validate_currency(currency):
            return json.dumps(create_error_response(ProtocolError("Unsupported currency")))
        
        socket = self._get_socket(currency)
        res = {'result': None, 'error': None}
        
        try:
            data = await socket.send_message("getblock", [hex_hash, verbose], timeout=30)
            
            if data in [-1, -2]:  # OS_ERROR or OTHER_EXCEPTION
                logger.error("[server] ERROR: Error during getblock grabbing!")
                res['error'] = -1
            else:
                res['result'] = data
                
        except Exception as e:
            logger.error(f"[server] ERROR: Error during getblock grabbing! {str(e)}")
            res['error'] = -1
        
        logger.debug(f"DEBUG MESSAGE: {str(res)}")
        return json.dumps(res)
    
    async def getblockhash(self, params: List[Any]) -> str:
        """
        Get block hash by height.
        
        Args:
            params: [currency, height]
            
        Returns:
            JSON string with block hash
        """
        currency = params[0]
        height = params[1]
        
        logger.info(f"[server] xrmgetblockhash: {currency} - {str(height)}")
        
        if not self._validate_currency(currency):
            return json.dumps(create_error_response(ProtocolError("Unsupported currency")))
        
        socket = self._get_socket(currency)
        res = {'result': None, 'error': None}
        
        try:
            data = await socket.send_message("getblockhash", [int(height)], timeout=30)
            
            if data in [-1, -2]:  # OS_ERROR or OTHER_EXCEPTION
                logger.error("[server] ERROR: Error during getblockhash grabbing!")
                res['error'] = -1
            else:
                res['result'] = data
                
        except Exception as e:
            logger.error(f"[server] ERROR: Error during getblockhash grabbing! {str(e)}")
            res['error'] = -1
        
        logger.debug(f"DEBUG MESSAGE: {str(res)}")
        return json.dumps(res)


class BalanceRPCHandler(BaseRPCHandler):
    """Handler for balance-related RPC methods."""
    
    async def getbalance(self, params: List[Any]) -> str:
        """
        Get balance for an address.
        
        Args:
            params: [currency, address]
            
        Returns:
            JSON string with balance data
        """
        currency = params[0]
        address = params[1]
        
        logger.info(f"[server] xrmgetbalance: {currency} - {str(address)}")
        
        if not self._validate_currency(currency):
            return json.dumps(create_error_response(ProtocolError("Unsupported currency")))
        
        socket = self._get_socket(currency)
        res = {'result': None, 'error': None}
        
        try:
            data = await socket.send_message("blockchain.address.get_balance", [str(address)], timeout=30)
            
            if data in [-1, -2]:  # OS_ERROR or OTHER_EXCEPTION
                logger.error("[server] ERROR: Error during getbalance grabbing!")
                res['error'] = -1
            else:
                if data['confirmed'] > 0:
                    data['confirmed'] = float(data['confirmed']) / 100000000.0
                
                if data['unconfirmed'] > 0:
                    data['unconfirmed'] = float(data['unconfirmed']) / 100000000.0
                
                res['result'] = data
                
        except Exception as e:
            logger.error(f"[server] ERROR: Error during getbalance grabbing! {str(e)}")
            res['error'] = -1
        
        logger.debug(f"DEBUG MESSAGE: {str(res)}")
        return json.dumps(res)


class HistoryRPCHandler(BaseRPCHandler):
    """Handler for history-related RPC methods."""
    
    async def gethistory(self, params: List[Any]) -> str:
        """
        Get transaction history for addresses.
        
        Args:
            params: [currency, addresses]
            
        Returns:
            JSON string with history data
        """
        currency = params[0]
        
        # Parse addresses
        try:
            addresses = json.loads(params[1])
        except (TypeError, JSONDecodeError):
            addresses = params[1]
        
        if isinstance(addresses, str):
            addresses = addresses.split(',')
        
        if not addresses or not isinstance(addresses, list):
            return json.dumps([])
        
        timestart = TimestampMillisec64()
        logger.info(f"[server] {timestart} xrmgethistory: {currency}")
        
        if not self._validate_currency(currency):
            return json.dumps([])
        
        socket = self._get_socket(currency)
        
        try:
            res = await socket.send_batch("gethistory", addresses, timeout=60)
            
            if res is None or res in [-1, -2]:  # OS_ERROR or OTHER_EXCEPTION
                logging.info(f"[server] gethistory failed for coin: {currency}")
                return json.dumps([])
            
            # DEBUG! PURGE EMPTY LISTS IN LIST?
            res = [e for e in res if e]
            
            logger.debug(f"DEBUG MESSAGE: {str(res)}")
            logger.info(f"[server-end gethistory] completion time: {TimestampMillisec64() - timestart}ms")
            
            return json.dumps(res)
            
        except (NetworkError, ProtocolError) as e:
            logging.info(f"[server] gethistory failed for coin: {currency}")
            return json.dumps([])


class UtilityRPCHandler:
    """Handler for utility RPC methods."""
    
    async def ping(self) -> str:
        """Simple ping method for testing connectivity."""
        logger.info("[server] ping")
        res = {'result': 1, 'error': None}
        return json.dumps(res)