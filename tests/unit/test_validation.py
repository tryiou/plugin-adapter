#!/usr/bin/env python3
"""
Unit tests for Validation Logic.
Tests cover parameter validation functions and input sanitization.
"""

import json

from src.core.error_handling import ValidationError
from src.core.validation import (ParameterValidator, validate_address_list,
                                 validate_rpc_parameters)


class TestParameterValidator:
    """Test suite for ParameterValidator class."""

    def test_validate_rpc_params_valid_single_param(self):
        """Test validation of RPC parameters with single parameter."""
        params = ["BTC"]
        result = ParameterValidator.validate_rpc_params(params)
        assert result is None

    def test_validate_rpc_params_empty_list(self):
        """Test validation of empty parameter list."""
        params = []
        result = ParameterValidator.validate_rpc_params(params)
        assert isinstance(result, ValidationError)
        assert "Invalid parameters" in result.message

    def test_validate_rpc_params_none(self):
        """Test validation of None parameters."""
        result = ParameterValidator.validate_rpc_params(None)
        assert isinstance(result, ValidationError)
        assert "Invalid parameters" in result.message

    def test_validate_rpc_params_currency_none(self):
        """Test validation with None currency."""
        params = [None]
        result = ParameterValidator.validate_rpc_params(params)
        assert isinstance(result, ValidationError)
        assert "Invalid currency parameter" in result.message

    def test_validate_rpc_params_currency_empty_string(self):
        """Test validation with empty currency string."""
        params = [""]
        result = ParameterValidator.validate_rpc_params(params)
        assert isinstance(result, ValidationError)
        assert "Invalid currency parameter" in result.message

    def test_validate_addresses_empty(self):
        """Test address validation with empty input."""
        result = ParameterValidator.validate_addresses(None)
        assert result == []

        result = ParameterValidator.validate_addresses("")
        assert result == []

        result = ParameterValidator.validate_addresses([])
        assert result == []

    def test_validate_addresses_string_list(self):
        """Test address validation with string list."""
        addresses = ["address1", "address2", "address3"]
        result = ParameterValidator.validate_addresses(addresses)
        assert result == addresses

    def test_validate_addresses_comma_separated_string(self):
        """Test address validation with comma-separated string."""
        address_string = "address1,address2,address3"
        result = ParameterValidator.validate_addresses(address_string)
        expected = ["address1", "address2", "address3"]
        assert result == expected

    def test_validate_addresses_json_string(self):
        """Test address validation with JSON string."""
        address_list = ["address1", "address2", "address3"]
        address_json = json.dumps(address_list)
        result = ParameterValidator.validate_addresses(address_json)
        assert result == address_list

    def test_validate_addresses_mixed_types(self):
        """Test address validation with mixed types in list."""
        addresses = ["valid_address", 123, None, "another_valid", "", "   "]
        result = ParameterValidator.validate_addresses(addresses)
        expected = ["valid_address", "another_valid"]
        assert result == expected

    def test_validate_addresses_with_whitespace(self):
        """Test address validation with whitespace in addresses."""
        addresses = [" address1 ", "address2", " address3 "]
        result = ParameterValidator.validate_addresses(addresses)
        expected = ["address1", "address2", "address3"]
        assert result == expected

    def test_validate_transaction_params_valid(self):
        """Test transaction parameter validation with valid input."""
        params = ["BTC", "rawtx123"]
        result = ParameterValidator.validate_transaction_params(params)
        assert result is None

    def test_validate_transaction_params_missing_rawtx(self):
        """Test transaction parameter validation with missing rawtx."""
        params = ["BTC"]
        result = ParameterValidator.validate_transaction_params(params)
        assert isinstance(result, ValidationError)
        assert "Invalid raw transaction" in result.message

    def test_validate_transaction_params_invalid_rawtx(self):
        """Test transaction parameter validation with invalid rawtx."""
        params = ["BTC", None]
        result = ParameterValidator.validate_transaction_params(params)
        assert isinstance(result, ValidationError)
        assert "Invalid raw transaction" in result.message

    def test_validate_block_params_valid(self):
        """Test block parameter validation with valid input."""
        params = ["BTC", "block_hash_123"]
        result = ParameterValidator.validate_block_params(params)
        assert result is None

    def test_validate_block_params_missing_block_param(self):
        """Test block parameter validation with missing block parameter."""
        params = ["BTC"]
        result = ParameterValidator.validate_block_params(params)
        assert isinstance(result, ValidationError)
        assert "Block hash/height parameter is required" in result.message

    def test_validate_balance_params_valid(self):
        """Test balance parameter validation with valid input."""
        params = ["BTC", "address123"]
        result = ParameterValidator.validate_balance_params(params)
        assert result is None

    def test_validate_balance_params_missing_address(self):
        """Test balance parameter validation with missing address."""
        params = ["BTC"]
        result = ParameterValidator.validate_balance_params(params)
        assert isinstance(result, ValidationError)
        assert "Invalid address parameter" in result.message

    def test_validate_balance_params_none_address(self):
        """Test balance parameter validation with None address."""
        params = ["BTC", None]
        result = ParameterValidator.validate_balance_params(params)
        assert isinstance(result, ValidationError)
        assert "Invalid address parameter" in result.message


class TestValidationConvenienceFunctions:
    """Test suite for validation convenience functions."""

    def test_validate_rpc_parameters_function(self):
        """Test the validate_rpc_parameters convenience function."""
        # Test valid parameters
        result = validate_rpc_parameters(["BTC"])
        assert result is None

        # Test invalid parameters
        result = validate_rpc_parameters([])
        assert isinstance(result, ValidationError)

    def test_validate_address_list_function(self):
        """Test the validate_address_list convenience function."""
        # Test valid addresses
        addresses = ["address1", "address2"]
        result = validate_address_list(addresses)
        assert result == addresses

        # Test invalid addresses
        result = validate_address_list(None)
        assert result == []

        # Test string input
        address_string = "address1,address2"
        result = validate_address_list(address_string)
        expected = ["address1", "address2"]
        assert result == expected
