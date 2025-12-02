#!/usr/bin/env python3

import datetime
import logging
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar

from src.core.application import PluginAdapterApplication
from src.core.configuration import config_manager
from src.core.constants import ConfigConstants
from src.core.errors import ValidationError
from src.core.validation import ParameterValidator
from src.networking.tcp_socket import TCPSocket
from src.utils.operation_logger import OperationLogger
from src.utils.response_helper import ResponseHelper

# Type variable for decorator
F = TypeVar('F', bound=Callable[..., Any])

logger = logging.getLogger(__name__)


def validate_rpc_params(params: List[Any], min_length: int = 1) -> Optional[ValidationError]:
    """
    Centralized parameter validation for RPC methods using ParameterValidator.
    
    Args:
        params: Parameters to validate
        min_length: Minimum required length for params list
        
    Returns:
        ValidationError if validation fails, None if valid
    """
    return ParameterValidator.validate_rpc_params(params, min_length)


def TimestampMillisec64() -> int:
    """Get current timestamp in milliseconds since Unix epoch."""
    return int(
        (datetime.datetime.utcnow() - datetime.datetime(ConfigConstants.UNIX_EPOCH_YEAR, 1, 1)).total_seconds() * 1000)


def parse_response(response: Any) -> Optional[List[Dict[str, Any]]]:
    """
    Parse UTXO response data into standardized format.
    
    Args:
        response: Raw response from ElectrumX server
        
    Returns:
        Parsed UTXO data or None if parsing fails
    """
    refined_result = []

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
        OperationLogger.error("parse_response", "system", e)
        return None


class BaseRPCHandler:
    """Base class for all RPC handlers providing common functionality."""

    def __init__(self, app: PluginAdapterApplication):
        """Initialize the base handler with application instance."""
        self.app = app

    def _validate_currency(self, currency: str) -> None:
        """
        Validate that a currency is supported and configured.
        
        Args:
            currency: Currency symbol to validate
            
        Raises:
            ValidationError: If currency is not supported or configured
        """
        if not currency or not isinstance(currency, str):
            raise ValidationError("Currency parameter is required and must be a string")

        if not config_manager.has_currency(currency):
            OperationLogger.warning("_validate_currency", currency,
                                    ValidationError(f"Unsupported currency: {currency}"))
            raise ValidationError(f"Unsupported currency: {currency}")

    def _parse_addresses(self, raw_addresses: Any) -> List[str]:
        """
        Extract and validate addresses using centralized validator.
        
        Args:
            raw_addresses: Raw addresses in various formats
            
        Returns:
            List of validated address strings
        """
        return ParameterValidator.validate_addresses(raw_addresses)


class UTXORPCHandler(BaseRPCHandler):
    """Handler for UTXO-related RPC methods."""

    async def getutxos(self, params: List[Any], socket: Optional[TCPSocket] = None) -> str:
        """
        Get UTXOs for specified addresses.
        
        Args:
            params: [currency, addresses]
            socket: Connected TCPSocket instance (optional)
            
        Returns:
            JSON string with UTXO data
        """
        currency = params[0]
        start_time = int(time.time() * 1000)

        try:
            # DEBUG: Log parameters
            OperationLogger.debug_params("getutxos", currency, params)

            addresses = self._parse_addresses(params[1])
            if not addresses:
                return ResponseHelper.error("No valid addresses provided")

            if socket is None:
                socket = await self.app.connection_manager.get_socket(currency)

            data = await socket.send_batch(
                "blockchain.address.listunspent", addresses, timeout=ConfigConstants.TIMEOUT_UTXO
            )

            result = parse_response(data) if data else None
            if not result:
                duration = int(time.time() * 1000) - start_time
                OperationLogger.success("getutxos", currency, duration, {"currency": currency, "result_count": 0})
                return ResponseHelper.utxos([])

            duration = int(time.time() * 1000) - start_time
            OperationLogger.debug_result("getutxos", currency, result, duration)
            OperationLogger.success("getutxos", currency, duration, {"currency": currency, "result_count": len(result)})
            return ResponseHelper.utxos(result)

        except Exception as e:
            duration = int(time.time() * 1000) - start_time
            OperationLogger.debug_error("getutxos", currency, e)
            OperationLogger.success("getutxos", currency, duration, {"currency": currency, "success": False})
            return ResponseHelper.from_exception(e)


class TransactionRPCHandler(BaseRPCHandler):
    """Handler for transaction-related RPC methods."""

    async def getrawtransaction(self, params: List[Any], socket: Optional[TCPSocket] = None) -> str:
        """
        Get raw transaction data.
        
        Args:
            params: [currency, txid, verbose?]
            socket: Connected TCPSocket instance (optional)
            
        Returns:
            JSON string with transaction data
        """
        currency = params[0]
        start_time = int(time.time() * 1000)

        try:
            txid = params[1]
            verbose = False

            if len(params) >= 3:
                v = params[2]
                if any(x == v for x in [True, 'true', 'True', '1', 1]):
                    verbose = True

            # DEBUG: Log parameters
            OperationLogger.debug_params("getrawtransaction", currency, params)

            # Validate currency (will raise ValidationError if invalid)
            self._validate_currency(currency)

            # Validate transaction parameters
            validation_error = ParameterValidator.validate_transaction_params(params)
            if validation_error:
                duration = int(time.time() * 1000) - start_time
                OperationLogger.debug_error("getrawtransaction", currency, validation_error)
                OperationLogger.success("getrawtransaction", currency, duration,
                                        {"currency": currency, "success": False})
                return ResponseHelper.from_exception(validation_error)

            if socket is None:
                socket = await self.app.connection_manager.get_socket(currency)

            data = await socket.send_message(
                "blockchain.transaction.get", [txid, verbose], timeout=ConfigConstants.TIMEOUT_TRANSACTIONS
            )

            duration = int(time.time() * 1000) - start_time
            OperationLogger.debug_result("getrawtransaction", currency, data, duration)
            OperationLogger.success("getrawtransaction", currency, duration,
                                    {"currency": currency, "result_size": len(str(data))})
            return ResponseHelper.transaction(data)

        except Exception as e:
            duration = int(time.time() * 1000) - start_time
            OperationLogger.debug_error("getrawtransaction", currency, e)
            OperationLogger.success("getrawtransaction", currency, duration, {"currency": currency, "success": False})
            return ResponseHelper.from_exception(e)

    async def getrawmempool(self, params: List[Any], socket: Optional[TCPSocket] = None) -> str:
        """
        Get raw mempool data.
        
        Args:
            params: [currency, verbose?]
            socket: Connected TCPSocket instance (optional)
            
        Returns:
            JSON string with mempool data
        """
        currency = params[0]
        start_time = int(time.time() * 1000)

        try:
            verbose = False

            if len(params) >= 2:
                v = params[1]
                if any(x == v for x in [True, 'true', 'True', '1', 1]):
                    verbose = True

            # DEBUG: Log parameters
            OperationLogger.debug_params("getrawmempool", currency, params)

            # Validate currency (will raise ValidationError if invalid)
            self._validate_currency(currency)

            if socket is None:
                socket = await self.app.connection_manager.get_socket(currency)

            data = await socket.send_message(
                "getrawmempool", [verbose], timeout=ConfigConstants.TIMEOUT_TRANSACTIONS
            )

            duration = int(time.time() * 1000) - start_time
            OperationLogger.debug_result("getrawmempool", currency, data, duration)
            OperationLogger.success("getrawmempool", currency, duration,
                                    {"currency": currency, "result_size": len(str(data))})
            return ResponseHelper.success(data)

        except Exception as e:
            duration = int(time.time() * 1000) - start_time
            OperationLogger.debug_error("getrawmempool", currency, e)
            OperationLogger.success("getrawmempool", currency, duration, {"currency": currency, "success": False})
            return ResponseHelper.from_exception(e)

    async def sendrawtransaction(self, params: List[Any], socket: Optional[TCPSocket] = None) -> str:
        """
        Broadcast a raw transaction.
        
        Args:
            params: [currency, rawtx]
            socket: Connected TCPSocket instance (optional)
            
        Returns:
            JSON string with transaction ID or error
        """
        currency = params[0]
        start_time = int(time.time() * 1000)

        try:
            rawtx = params[1]

            # DEBUG: Log parameters
            OperationLogger.debug_params("sendrawtransaction", currency, params)

            # Validate currency (will raise ValidationError if invalid)
            self._validate_currency(currency)

            # Validate transaction parameters
            validation_error = ParameterValidator.validate_transaction_params(params)
            if validation_error:
                duration = int(time.time() * 1000) - start_time
                OperationLogger.debug_error("sendrawtransaction", currency, validation_error)
                OperationLogger.success("sendrawtransaction", currency, duration,
                                        {"currency": currency, "success": False})
                return ResponseHelper.from_exception(validation_error)

            if socket is None:
                socket = await self.app.connection_manager.get_socket(currency)

            data = await socket.send_message(
                "blockchain.transaction.broadcast", [rawtx], timeout=ConfigConstants.TIMEOUT_TRANSACTIONS
            )

            duration = int(time.time() * 1000) - start_time
            OperationLogger.debug_result("sendrawtransaction", currency, data, duration)
            OperationLogger.success("sendrawtransaction", currency, duration,
                                    {"currency": currency, "result_size": len(str(data))})
            return ResponseHelper.success(data)

        except Exception as e:
            duration = int(time.time() * 1000) - start_time
            OperationLogger.debug_error("sendrawtransaction", currency, e)
            OperationLogger.success("sendrawtransaction", currency, duration, {"currency": currency, "success": False})
            return ResponseHelper.from_exception(e)

    async def gettransaction(self, params: List[Any], socket: Optional[TCPSocket] = None) -> str:
        """
        Get transaction details.
        
        Args:
            params: [currency, txid]
            socket: Connected TCPSocket instance (optional)
            
        Returns:
            JSON string with transaction data
        """
        currency = params[0]
        start_time = int(time.time() * 1000)

        try:
            txid = params[1]
            verbose = True

            # DEBUG: Log parameters
            OperationLogger.debug_params("gettransaction", currency, params)

            # Validate currency (will raise ValidationError if invalid)
            self._validate_currency(currency)

            # Validate transaction parameters
            validation_error = ParameterValidator.validate_transaction_params(params)
            if validation_error:
                duration = int(time.time() * 1000) - start_time
                OperationLogger.debug_error("gettransaction", currency, validation_error)
                OperationLogger.success("gettransaction", currency, duration, {"currency": currency, "success": False})
                return ResponseHelper.from_exception(validation_error)

            if socket is None:
                socket = await self.app.connection_manager.get_socket(currency)

            data = await socket.send_message(
                "blockchain.transaction.get", [txid, verbose], timeout=ConfigConstants.TIMEOUT_TRANSACTIONS
            )

            duration = int(time.time() * 1000) - start_time
            OperationLogger.debug_result("gettransaction", currency, data, duration)
            OperationLogger.success("gettransaction", currency, duration,
                                    {"currency": currency, "result_size": len(str(data))})
            return ResponseHelper.transaction(data)

        except Exception as e:
            duration = int(time.time() * 1000) - start_time
            OperationLogger.debug_error("gettransaction", currency, e)
            OperationLogger.success("gettransaction", currency, duration, {"currency": currency, "success": False})
            return ResponseHelper.from_exception(e)

    async def get_plugin_fees(self, params: List[Any], socket: Optional[TCPSocket] = None) -> str:
        """
        Get relay fee for monitoring purposes using mempool.get_info.
        
        This method is specifically designed for monitoring endpoints and
        uses the modern mempool.get_info protocol method instead of the
        deprecated blockchain.relayfee.
        
        Args:
            params: [currency]
            socket: Connected TCPSocket instance (optional)
            
        Returns:
            JSON string with relay fee or None if not supported
        """
        currency = params[0]
        start_time = int(time.time() * 1000)

        try:
            # DEBUG: Log parameters
            OperationLogger.debug_params("get_plugin_fees", currency, params)

            # Validate currency (will raise ValidationError if invalid)
            self._validate_currency(currency)

            if socket is None:
                socket = await self.app.connection_manager.get_socket(currency)

            data = await socket.send_message("blockchain.relayfee", [], timeout=ConfigConstants.TIMEOUT_FEES)

            # Handle the relayfee response
            if data is not None:
                try:
                    fee_float = float(data)
                    duration = int(time.time() * 1000) - start_time
                    OperationLogger.debug_result("get_plugin_fees", currency, fee_float, duration)
                    OperationLogger.success("get_plugin_fees", currency, duration,
                                            {"currency": currency, "fee": fee_float})
                    return ResponseHelper.success(fee_float)
                except (ValueError, TypeError) as parse_error:
                    duration = int(time.time() * 1000) - start_time
                    OperationLogger.debug_error("get_plugin_fees", currency, parse_error)
                    OperationLogger.success("get_plugin_fees", currency, duration,
                                            {"currency": currency, "success": False})
                    return ResponseHelper.success(None)
            else:
                duration = int(time.time() * 1000) - start_time
                OperationLogger.debug_error("get_plugin_fees", currency, Exception("data is None"))
                OperationLogger.success("get_plugin_fees", currency, duration, {"currency": currency, "success": False})
                return ResponseHelper.success(None)

        except Exception as e:
            duration = int(time.time() * 1000) - start_time
            OperationLogger.debug_error("get_plugin_fees", currency, e)
            OperationLogger.success("get_plugin_fees", currency, duration, {"currency": currency, "success": False})
            return ResponseHelper.from_exception(e)


class BlockRPCHandler(BaseRPCHandler):
    """Handler for block-related RPC methods."""

    async def getblockcount(self, params: List[Any], socket: Optional[TCPSocket] = None) -> str:
        """
        Get current block count.
        
        Args:
            params: [currency]
            socket: Connected TCPSocket instance (optional)
            
        Returns:
            JSON string with block count
        """
        currency = params[0]
        start_time = int(time.time() * 1000)

        try:
            # DEBUG: Log parameters
            OperationLogger.debug_params("getblockcount", currency, params)

            # Validate currency (will raise ValidationError if invalid)
            self._validate_currency(currency)

            if socket is None:
                socket = await self.app.connection_manager.get_socket(currency)

            data = await socket.send_message(
                "getblockcount", (), timeout=ConfigConstants.TIMEOUT_BLOCK_COUNT
            )

            duration = int(time.time() * 1000) - start_time
            OperationLogger.debug_result("getblockcount", currency, data, duration)
            OperationLogger.success("getblockcount", currency, duration, {"currency": currency, "height": data})
            return ResponseHelper.success(data)

        except Exception as e:
            duration = int(time.time() * 1000) - start_time
            OperationLogger.debug_error("getblockcount", currency, e)
            OperationLogger.success("getblockcount", currency, duration, {"currency": currency, "success": False})
            return ResponseHelper.from_exception(e)

    async def getblock(self, params: List[Any], socket: Optional[TCPSocket] = None) -> str:
        """
        Get block data by hash.
        
        Args:
            params: [currency, hex_hash, verbose?]
            socket: Connected TCPSocket instance (optional)
            
        Returns:
            JSON string with block data
        """
        currency = params[0]
        start_time = int(time.time() * 1000)

        try:
            hex_hash = params[1]
            verbose = False

            if len(params) >= 3:
                v = params[2]
                if any(x == v for x in [True, 'true', 'True', '1', 1]):
                    verbose = True

            # DEBUG: Log parameters
            OperationLogger.debug_params("getblock", currency, params)

            # Validate currency (will raise ValidationError if invalid)
            self._validate_currency(currency)

            # Validate block parameters
            validation_error = ParameterValidator.validate_block_params(params)
            if validation_error:
                duration = int(time.time() * 1000) - start_time
                OperationLogger.debug_error("getblock", currency, validation_error)
                OperationLogger.success("getblock", currency, duration, {"currency": currency, "success": False})
                return ResponseHelper.from_exception(validation_error)

            if socket is None:
                socket = await self.app.connection_manager.get_socket(currency)

            data = await socket.send_message(
                "getblock", [hex_hash, verbose], timeout=ConfigConstants.TIMEOUT_TRANSACTIONS
            )

            duration = int(time.time() * 1000) - start_time
            if isinstance(data, dict) and 'tx' in data:
                OperationLogger.debug_result("getblock", currency, data, duration)
                OperationLogger.success("getblock", currency, duration,
                                        {"currency": currency, "tx_count": len(data['tx'])})
            else:
                OperationLogger.debug_result("getblock", currency, data, duration)
                OperationLogger.success("getblock", currency, duration,
                                        {"currency": currency, "result_size": len(str(data))})
            return ResponseHelper.success(data)

        except Exception as e:
            duration = int(time.time() * 1000) - start_time
            OperationLogger.debug_error("getblock", currency, e)
            OperationLogger.success("getblock", currency, duration, {"currency": currency, "success": False})
            return ResponseHelper.from_exception(e)

    async def getblockhash(self, params: List[Any], socket: Optional[TCPSocket] = None) -> str:
        """
        Get block hash by height.
        
        Args:
            params: [currency, height]
            socket: Connected TCPSocket instance (optional)
            
        Returns:
            JSON string with block hash
        """
        currency = params[0]
        start_time = int(time.time() * 1000)

        try:
            height = params[1]

            # DEBUG: Log parameters
            OperationLogger.debug_params("getblockhash", currency, params)

            # Validate currency (will raise ValidationError if invalid)
            self._validate_currency(currency)

            # Validate block parameters
            validation_error = ParameterValidator.validate_block_params(params)
            if validation_error:
                duration = int(time.time() * 1000) - start_time
                OperationLogger.debug_error("getblockhash", currency, validation_error)
                OperationLogger.success("getblockhash", currency, duration, {"currency": currency, "success": False})
                return ResponseHelper.from_exception(validation_error)

            if socket is None:
                socket = await self.app.connection_manager.get_socket(currency)

            data = await socket.send_message(
                "getblockhash", [int(height)], timeout=ConfigConstants.TIMEOUT_TRANSACTIONS
            )

            duration = int(time.time() * 1000) - start_time
            OperationLogger.debug_result("getblockhash", currency, data, duration)
            OperationLogger.success("getblockhash", currency, duration, {"currency": currency, "height": height})
            return ResponseHelper.success(data)

        except Exception as e:
            duration = int(time.time() * 1000) - start_time
            OperationLogger.debug_error("getblockhash", currency, e)
            OperationLogger.success("getblockhash", currency, duration, {"currency": currency, "success": False})
            return ResponseHelper.from_exception(e)


class BalanceRPCHandler(BaseRPCHandler):
    """Handler for balance-related RPC methods."""

    async def getbalance(self, params: List[Any], socket: Optional[TCPSocket] = None) -> str:
        """
        Get balance for an address.
        
        Args:
            params: [currency, address]
            socket: Connected TCPSocket instance (optional)
            
        Returns:
            JSON string with balance data
        """
        currency = params[0]
        start_time = int(time.time() * 1000)

        try:
            address = params[1]

            # DEBUG: Log parameters
            OperationLogger.debug_params("getbalance", currency, params)

            # Validate currency (will raise ValidationError if invalid)
            self._validate_currency(currency)

            # Validate balance parameters
            validation_error = ParameterValidator.validate_balance_params(params)
            if validation_error:
                duration = int(time.time() * 1000) - start_time
                OperationLogger.debug_error("getbalance", currency, validation_error)
                OperationLogger.success("getbalance", currency, duration, {"currency": currency, "success": False})
                return ResponseHelper.from_exception(validation_error)

            if socket is None:
                socket = await self.app.connection_manager.get_socket(currency)

            data = await socket.send_message(
                "blockchain.address.get_balance", [str(address)], timeout=ConfigConstants.TIMEOUT_BALANCE
            )

            if isinstance(data, dict):
                if data.get('confirmed', 0) > 0:
                    data['confirmed'] = float(data['confirmed']) / 100000000.0

                if data.get('unconfirmed', 0) > 0:
                    data['unconfirmed'] = float(data['unconfirmed']) / 100000000.0

            duration = int(time.time() * 1000) - start_time
            OperationLogger.debug_result("getbalance", currency, data, duration)
            OperationLogger.success("getbalance", currency, duration,
                                    {"currency": currency, "result_size": len(str(data))})
            return ResponseHelper.balance(data)

        except Exception as e:
            duration = int(time.time() * 1000) - start_time
            OperationLogger.debug_error("getbalance", currency, e)
            OperationLogger.success("getbalance", currency, duration, {"currency": currency, "success": False})
            return ResponseHelper.from_exception(e)


class HistoryRPCHandler(BaseRPCHandler):
    """Handler for history-related RPC methods."""

    async def gethistory(self, params: List[Any], socket: Optional[TCPSocket] = None) -> str:
        """
        Get transaction history for addresses.
        
        Args:
            params: [currency, addresses]
            socket: Connected TCPSocket instance (optional)
            
        Returns:
            JSON string with history data
        """
        currency = params[0]
        start_time = int(time.time() * 1000)

        try:
            addresses = self._parse_addresses(params[1])
            if not addresses:
                duration = int(time.time() * 1000) - start_time
                OperationLogger.debug_error("gethistory", currency, ValidationError("No valid addresses provided"))
                OperationLogger.success("gethistory", currency, duration, {"currency": currency, "success": False})
                return ResponseHelper.error("No valid addresses provided")

            # DEBUG: Log parameters
            OperationLogger.debug_params("gethistory", currency, params)

            if socket is None:
                socket = await self.app.connection_manager.get_socket(currency)

            res = await socket.send_batch(
                "gethistory", addresses, timeout=ConfigConstants.TIMEOUT_HISTORY
            )

            if res is None:
                duration = int(time.time() * 1000) - start_time
                OperationLogger.debug_result("gethistory", currency, [], duration)
                OperationLogger.success("gethistory", currency, duration, {"currency": currency, "result_count": 0})
                return ResponseHelper.history([])

            # Filter out empty results
            res = [e for e in res if e]

            duration = int(time.time() * 1000) - start_time
            OperationLogger.debug_result("gethistory", currency, res, duration)
            OperationLogger.success("gethistory", currency, duration, {"currency": currency, "result_count": len(res)})
            return ResponseHelper.history(res)

        except Exception as e:
            duration = int(time.time() * 1000) - start_time
            OperationLogger.debug_error("gethistory", currency, e)
            OperationLogger.success("gethistory", currency, duration, {"currency": currency, "success": False})
            return ResponseHelper.from_exception(e)


class UtilityRPCHandler:
    """Handler for utility RPC methods."""

    async def ping(self) -> str:
        """Simple ping method for testing connectivity."""
        start_time = int(time.time() * 1000)
        response = ResponseHelper.ping()
        duration = int(time.time() * 1000) - start_time
        OperationLogger.success("ping", "system", duration)
        return response
