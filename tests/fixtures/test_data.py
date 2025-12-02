"""
Test Data Management for Plugin-Adapter Testing

This module provides comprehensive test data management including:
- Sample data generators
- Test scenarios
- Data validation
- Data cleanup utilities
"""

import asyncio
import json
import random
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class TestCurrency:
    """Test currency configuration."""
    symbol: str
    host: str
    port: int
    description: str = ""
    enabled: bool = True


@dataclass
class TestAddress:
    """Test address configuration."""
    address: str
    currency: str
    private_key: Optional[str] = None
    public_key: Optional[str] = None


@dataclass
class TestUTXO:
    """Test UTXO data."""
    tx_hash: str
    tx_pos: int
    height: int
    value: int
    address: str
    currency: str
    confirmed: bool = True


@dataclass
class TestTransaction:
    """Test transaction data."""
    txid: str
    version: int = 1
    locktime: int = 0
    inputs: List[Dict[str, Any]] = None
    outputs: List[Dict[str, Any]] = None
    block_hash: Optional[str] = None
    block_height: Optional[int] = None
    confirmations: int = 0
    time: int = 0
    size: int = 250
    fee: Optional[int] = None
    currency: str = "BTC"


@dataclass
class TestBlock:
    """Test block data."""
    hash: str
    height: int
    version: int = 536870912
    merkleroot: str = ""
    time: int = 0
    nonce: int = 0
    bits: str = "1d00ffff"
    difficulty: float = 1.0
    previousblockhash: Optional[str] = None
    nextblockhash: Optional[str] = None
    transaction_count: int = 0
    currency: str = "BTC"


class TestDataGenerator:
    """Generator for test data."""

    def __init__(self):
        self._counter = 0

    def generate_currency(self, symbol: str = None, host: str = "localhost",
                          port: int = None, description: str = "") -> TestCurrency:
        """Generate a test currency."""
        if symbol is None:
            symbols = ["BTC", "LTC", "DOGE", "DASH", "BCH", "RVN", "SYS", "TZC", "XSN", "UNO"]
            symbol = random.choice(symbols)

        if port is None:
            port = 8000 + len(symbol) * 100 + random.randint(1, 99)

        return TestCurrency(
            symbol=symbol,
            host=host,
            port=port,
            description=description or f"{symbol} test currency"
        )

    def generate_address(self, currency: str = "BTC", prefix: str = "bc1q") -> TestAddress:
        """Generate a test address."""
        address = f"{prefix}{self._generate_random_string(32)}"
        return TestAddress(
            address=address,
            currency=currency
        )

    def generate_utxo(self, address: str = None, currency: str = "BTC",
                      value: int = None, height: int = None) -> TestUTXO:
        """Generate a test UTXO."""
        if address is None:
            address = self.generate_address(currency).address

        if value is None:
            # Generate random value between 0.001 and 10 BTC (in satoshis)
            value = random.randint(100000, 1000000000)

        if height is None:
            height = random.randint(1000, 1000000)

        return TestUTXO(
            tx_hash=self._generate_tx_hash(),
            tx_pos=random.randint(0, 10),
            height=height,
            value=value,
            address=address,
            currency=currency,
            confirmed=random.choice([True, True, True, False])  # 75% chance of being confirmed
        )

    def generate_transaction(self, currency: str = "BTC", inputs_count: int = 1,
                             outputs_count: int = 1, confirmed: bool = True) -> TestTransaction:
        """Generate a test transaction."""
        txid = self._generate_tx_hash()

        # Generate inputs
        inputs = []
        for i in range(inputs_count):
            inputs.append({
                "txid": self._generate_tx_hash(),
                "vout": random.randint(0, 10),
                "address": self.generate_address(currency).address,
                "value": random.randint(100000, 100000000)
            })

        # Generate outputs
        outputs = []
        total_input_value = sum(input["value"] for input in inputs)
        for i in range(outputs_count):
            if i == outputs_count - 1:
                # Last output gets remaining value
                value = total_input_value - sum(output["value"] for output in outputs)
            else:
                # Random value for other outputs
                max_value = max(100000, total_input_value // outputs_count)
                value = random.randint(10000, max_value)

            outputs.append({
                "address": self.generate_address(currency).address,
                "value": value
            })

        fee = total_input_value - sum(output["value"] for output in outputs)

        block_height = random.randint(1000, 1000000) if confirmed else None
        block_hash = self._generate_block_hash() if confirmed else None
        confirmations = random.randint(1, 1000) if confirmed else 0

        return TestTransaction(
            txid=txid,
            version=random.choice([1, 2]),
            locktime=random.randint(0, 1000000),
            inputs=inputs,
            outputs=outputs,
            block_hash=block_hash,
            block_height=block_height,
            confirmations=confirmations,
            time=int(time.time()) - random.randint(0, 86400 * 30),  # Last 30 days
            size=random.randint(100, 2000),
            fee=fee,
            currency=currency
        )

    def generate_block(self, height: int = None, currency: str = "BTC",
                       transaction_count: int = None) -> TestBlock:
        """Generate a test block."""
        if height is None:
            height = random.randint(1000, 1000000)

        if transaction_count is None:
            transaction_count = random.randint(1, 2000)

        return TestBlock(
            hash=self._generate_block_hash(),
            height=height,
            version=random.choice([536870912, 1073741824, 0]),
            merkleroot=self._generate_tx_hash(),
            time=int(time.time()) - random.randint(0, 86400 * 7),  # Last 7 days
            nonce=random.randint(0, 2 ** 32 - 1),
            bits=random.choice(["1d00ffff", "1c00ffff", "1b00ffff"]),
            difficulty=random.uniform(1.0, 1000000.0),
            previousblockhash=self._generate_block_hash() if height > 0 else None,
            nextblockhash=self._generate_block_hash(),
            transaction_count=transaction_count,
            currency=currency
        )

    def _generate_random_string(self, length: int) -> str:
        """Generate a random hexadecimal string."""
        import string
        chars = string.hexdigits.lower()
        return ''.join(random.choice(chars) for _ in range(length))

    def _generate_tx_hash(self) -> str:
        """Generate a random transaction hash."""
        return self._generate_random_string(64)

    def _generate_block_hash(self) -> str:
        """Generate a random block hash."""
        return self._generate_random_string(64)

    def generate_configuration(self, currencies_count: int = 3) -> Dict[str, Any]:
        """Generate a complete test configuration."""
        currencies = {}

        for i in range(currencies_count):
            currency = self.generate_currency()
            currencies[currency.symbol] = {
                "host": currency.host,
                "port": currency.port,
                "description": currency.description
            }

        return {
            "currencies": currencies,
            "server": {
                "port": 5000,
                "host": "0.0.0.0"
            },
            "timeouts": {
                "default": 30,
                "block_count": 2,
                "utxo": 30,
                "transactions": 10
            },
            "max_connections": 3
        }


class TestScenario:
    """Test scenario definition."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.data = {}
        self.setup_steps = []
        self.cleanup_steps = []

    def add_data(self, key: str, value: Any):
        """Add test data to the scenario."""
        self.data[key] = value
        return self

    def add_setup_step(self, step: callable, *args, **kwargs):
        """Add a setup step to the scenario."""
        self.setup_steps.append((step, args, kwargs))
        return self

    def add_cleanup_step(self, step: callable, *args, **kwargs):
        """Add a cleanup step to the scenario."""
        self.cleanup_steps.append((step, args, kwargs))
        return self

    async def setup(self):
        """Execute all setup steps."""
        for step, args, kwargs in self.setup_steps:
            if asyncio.iscoroutinefunction(step):
                await step(*args, **kwargs)
            else:
                step(*args, **kwargs)

    async def cleanup(self):
        """Execute all cleanup steps."""
        for step, args, kwargs in self.cleanup_steps:
            if asyncio.iscoroutinefunction(step):
                await step(*args, **kwargs)
            else:
                step(*args, **kwargs)


class TestScenarioFactory:
    """Factory for creating test scenarios."""

    @staticmethod
    def create_single_currency_scenario() -> TestScenario:
        """Create a scenario with a single currency."""
        generator = TestDataGenerator()

        scenario = TestScenario(
            "single_currency",
            "Test scenario with a single currency (BTC)"
        )

        # Add currency data
        btc = generator.generate_currency("BTC", port=8000)
        scenario.add_data("currencies", {"BTC": btc})

        # Add addresses
        addresses = [generator.generate_address("BTC") for _ in range(5)]
        scenario.add_data("addresses", addresses)

        # Add UTXOs
        utxos = [generator.generate_utxo(addr.address, "BTC") for addr in addresses]
        scenario.add_data("utxos", utxos)

        return scenario

    @staticmethod
    def create_multi_currency_scenario() -> TestScenario:
        """Create a scenario with multiple currencies."""
        generator = TestDataGenerator()

        scenario = TestScenario(
            "multi_currency",
            "Test scenario with multiple currencies"
        )

        # Add currencies
        currencies = [
            generator.generate_currency("BTC", port=8000),
            generator.generate_currency("LTC", port=8001),
            generator.generate_currency("DOGE", port=8002)
        ]
        scenario.add_data("currencies", {c.symbol: c for c in currencies})

        # Add addresses for each currency
        addresses = {}
        for currency in currencies:
            addresses[currency.symbol] = [generator.generate_address(currency.symbol) for _ in range(3)]
        scenario.add_data("addresses", addresses)

        # Add transactions
        transactions = []
        for currency in currencies:
            for _ in range(10):
                transactions.append(generator.generate_transaction(currency.symbol))
        scenario.add_data("transactions", transactions)

        return scenario

    @staticmethod
    def create_high_volume_scenario() -> TestScenario:
        """Create a scenario with high volume data."""
        generator = TestDataGenerator()

        scenario = TestScenario(
            "high_volume",
            "Test scenario with high volume data for performance testing"
        )

        # Add currencies
        currencies = ["BTC", "LTC", "DOGE"]
        scenario.add_data("currencies", {c: generator.generate_currency(c) for c in currencies})

        # Add many addresses
        addresses = []
        for currency in currencies:
            addresses.extend([generator.generate_address(currency) for _ in range(100)])
        scenario.add_data("addresses", addresses)

        # Add many UTXOs
        utxos = []
        for addr in addresses:
            utxos.extend([generator.generate_utxo(addr.address, addr.currency) for _ in range(10)])
        scenario.add_data("utxos", utxos)

        # Add many transactions
        transactions = []
        for _ in range(1000):
            currency = random.choice(currencies)
            transactions.append(generator.generate_transaction(currency))
        scenario.add_data("transactions", transactions)

        return scenario

    @staticmethod
    def create_error_scenario() -> TestScenario:
        """Create a scenario with error conditions."""
        generator = TestDataGenerator()

        scenario = TestScenario(
            "error_conditions",
            "Test scenario with various error conditions"
        )

        # Add invalid currency
        invalid_currency = TestCurrency(
            symbol="INVALID",
            host="nonexistent.host",
            port=9999,
            enabled=False
        )
        scenario.add_data("invalid_currency", invalid_currency)

        # Add invalid addresses
        invalid_addresses = [
            TestAddress(address="invalid_address", currency="BTC"),
            TestAddress(address="", currency="LTC"),
            TestAddress(address="bc1q" + "x" * 100, currency="DOGE")  # Too long
        ]
        scenario.add_data("invalid_addresses", invalid_addresses)

        # Add transactions with errors (using valid parameters only)
        error_transactions = [
            generator.generate_transaction("BTC", confirmed=False),  # Unconfirmed
            generator.generate_transaction("LTC", inputs_count=0),  # No inputs
            generator.generate_transaction("DOGE", outputs_count=0)  # No outputs
        ]
        scenario.add_data("error_transactions", error_transactions)

        return scenario


class TestDataValidator:
    """Validator for test data."""

    @staticmethod
    def validate_currency(currency: TestCurrency) -> List[str]:
        """Validate a currency configuration."""
        errors = []

        if not currency.symbol:
            errors.append("Currency symbol cannot be empty")

        if not currency.host:
            errors.append("Currency host cannot be empty")

        if not (1 <= currency.port <= 65535):
            errors.append(f"Invalid port {currency.port}, must be between 1 and 65535")

        return errors

    @staticmethod
    def validate_address(address: TestAddress) -> List[str]:
        """Validate an address."""
        errors = []

        if not address.address:
            errors.append("Address cannot be empty")

        if not address.currency:
            errors.append("Address currency cannot be empty")

        # Basic address format validation
        if not address.address.startswith(("bc1", "1", "3", "ltc1", "L", "M", "D", "X")):
            errors.append(f"Invalid address format: {address.address}")

        return errors

    @staticmethod
    def validate_utxo(utxo: TestUTXO) -> List[str]:
        """Validate a UTXO."""
        errors = []

        if not utxo.tx_hash:
            errors.append("UTXO tx_hash cannot be empty")

        if utxo.tx_pos < 0:
            errors.append(f"UTXO tx_pos cannot be negative: {utxo.tx_pos}")

        if utxo.height < 0:
            errors.append(f"UTXO height cannot be negative: {utxo.height}")

        if utxo.value < 0:
            errors.append(f"UTXO value cannot be negative: {utxo.value}")

        errors.extend(TestDataValidator.validate_address(TestAddress(
            address=utxo.address, currency=utxo.currency
        )))

        return errors

    @staticmethod
    def validate_transaction(tx: TestTransaction) -> List[str]:
        """Validate a transaction."""
        errors = []

        if not tx.txid:
            errors.append("Transaction txid cannot be empty")

        if tx.version <= 0:
            errors.append(f"Transaction version must be positive: {tx.version}")

        if tx.locktime < 0:
            errors.append(f"Transaction locktime cannot be negative: {tx.locktime}")

        if tx.inputs is None or len(tx.inputs) == 0:
            errors.append("Transaction must have at least one input")

        if tx.outputs is None or len(tx.outputs) == 0:
            errors.append("Transaction must have at least one output")

        # Validate inputs
        for i, input_data in enumerate(tx.inputs):
            if not input_data.get("txid"):
                errors.append(f"Input {i} txid cannot be empty")
            if input_data.get("vout", 0) < 0:
                errors.append(f"Input {i} vout cannot be negative")

        # Validate outputs
        for i, output_data in enumerate(tx.outputs):
            if not output_data.get("address"):
                errors.append(f"Output {i} address cannot be empty")
            if output_data.get("value", 0) < 0:
                errors.append(f"Output {i} value cannot be negative")

        return errors


class TestDataExporter:
    """Exporter for test data."""

    @staticmethod
    def export_to_json(data: Any, filename: str):
        """Export test data to JSON file."""
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    @staticmethod
    def export_scenario_to_file(scenario: TestScenario, filename: str):
        """Export a test scenario to a JSON file."""
        scenario_data = {
            "name": scenario.name,
            "description": scenario.description,
            "data": scenario.data,
            "timestamp": datetime.now().isoformat()
        }
        TestDataExporter.export_to_json(scenario_data, filename)

    @staticmethod
    def export_generator_data(generator: TestDataGenerator, count: int = 100,
                              filename: str = "test_data.json"):
        """Export generated test data to a file."""
        data = {
            "currencies": [asdict(generator.generate_currency()) for _ in range(count)],
            "addresses": [asdict(generator.generate_address()) for _ in range(count)],
            "utxos": [asdict(generator.generate_utxo()) for _ in range(count)],
            "transactions": [asdict(generator.generate_transaction()) for _ in range(count)],
            "blocks": [asdict(generator.generate_block()) for _ in range(count)],
            "timestamp": datetime.now().isoformat()
        }
        TestDataExporter.export_to_json(data, filename)


# Global test data instances
test_generator = TestDataGenerator()

# Pre-defined test scenarios
SINGLE_CURRENCY_SCENARIO = TestScenarioFactory.create_single_currency_scenario()
MULTI_CURRENCY_SCENARIO = TestScenarioFactory.create_multi_currency_scenario()
HIGH_VOLUME_SCENARIO = TestScenarioFactory.create_high_volume_scenario()
ERROR_SCENARIO = TestScenarioFactory.create_error_scenario()

# Test data sets
TEST_CURRENCIES = [
    TestCurrency("BTC", "localhost", 8000, "Bitcoin"),
    TestCurrency("LTC", "localhost", 8001, "Litecoin"),
    TestCurrency("DOGE", "localhost", 8002, "Dogecoin")
]

TEST_ADDRESSES = [
    TestAddress("bc1qtestaddress1", "BTC"),
    TestAddress("bc1qtestaddress2", "LTC"),
    TestAddress("D9Z3p2QJ2vKpQK7Q2vKpQK7Q2vKpQK7Q2v", "DOGE")
]
