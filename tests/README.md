# Plugin-Adapter Test Suite

This directory contains the comprehensive test suite for the plugin-adapter application, including unit tests,
integration tests, end-to-end tests, and performance benchmarks.

## Test Structure

```
tests/
├── __init__.py
├── README.md                 # This file
├── base_test_classes.py      # Base test classes and utilities
├── conftest.py              # Pytest configuration and fixtures
├── unit/                    # Unit tests for individual components
│   ├── __init__.py
│   ├── test_application.py
│   ├── test_configuration.py
│   ├── test_connection_manager.py
│   ├── test_error_handling.py
│   ├── test_response_factory.py
│   ├── test_rpc_handlers.py
│   ├── test_tcp_socket.py
│   ├── test_utils.py
│   └── test_validation.py
├── integration/             # Integration tests for component interactions
│   ├── __init__.py
│   ├── test_network_integration.py
│   └── test_rpc_integration.py
├── e2e/                     # End-to-end workflow tests
│   ├── __init__.py
│   └── test_full_workflow.py
├── performance/             # Performance benchmarks and load tests
│   ├── __init__.py
│   ├── test_benchmarks.py
│   └── test_load.py
├── examples/                # Example test configurations and scenarios
│   ├── __init__.py
│   └── test_configuration_examples.py
└── fixtures/                # Test fixtures and mock data
    ├── __init__.py
    ├── mock_configuration_manager.py
    ├── mock_electrumx_server.py
    ├── mock_tcp_socket.py
    └── test_data.py
```

## Test Categories

### Unit Tests (`tests/unit/`)

Unit tests focus on testing individual components in isolation:

- **Configuration Manager** (`test_configuration.py`): Tests environment variable parsing, currency validation,
  thread-safe access, hashX cache management, and error handling.
- **Error Handling System** (`test_error_handling.py`): Tests exception hierarchy, error decorator functionality, error
  response formatting, and error propagation.
- **Response Factory** (`test_response_factory.py`): Tests successful response creation, error response formatting,
  response serialization, and response validation.
- **Validation Logic** (`test_validation.py`): Tests parameter validation functions, input sanitization, validation
  error handling, and edge case validation.
- **Utilities** (`test_utils.py`): Tests logging functionality, response helper methods, and utility error handling.

### Integration Tests (`tests/integration/`)

Integration tests verify interactions between components:

- **Network Integration** (`test_network_integration.py`): Tests network communication, socket management, and protocol
  handling.
- **RPC Integration** (`test_rpc_integration.py`): Tests RPC method interactions, request/response handling, and error
  propagation.

### End-to-End Tests (`tests/e2e/`)

End-to-end tests verify complete workflows:

- **Full Workflow** (`test_full_workflow.py`): Tests complete application workflows from request to response.

### Performance Tests (`tests/performance/`)

Performance tests measure application performance under various conditions:

- **Benchmarks** (`test_benchmarks.py`): Comprehensive performance benchmarks for core components including execution
  time, memory usage, and throughput measurements.
- **Load Tests** (`test_load.py`): Tests application behavior under high load conditions.

## Test Fixtures and Mocks

### Mock Components

The test suite provides comprehensive mock implementations:

- **MockConfigurationManager**: Simulates configuration management with configurable test scenarios.
- **MockTCPSocket**: Simulates TCP socket communication with configurable delays, errors, and responses.
- **MockElectrumXServer**: Simulates ElectrumX server behavior for network testing.

### Test Data

- **TestDataGenerator**: Generates realistic test data for various scenarios.
- **TestScenarios**: Predefined test scenarios for different use cases.
- **TestValidators**: Validation utilities for test data integrity.

## Running Tests

### Prerequisites

Install test dependencies:

```bash
pip install -r requirements-test.txt
```

### Running All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=src --cov-report=html
```

### Running Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# End-to-end tests only
pytest tests/e2e/

# Performance tests only
pytest tests/performance/ -m performance
```

### Running Specific Tests

```bash
# Run specific test file
pytest tests/unit/test_configuration.py

# Run specific test class
pytest tests/unit/test_configuration.py::TestConfigurationManager

# Run specific test method
pytest tests/unit/test_configuration.py::TestConfigurationManager::test_load_from_environment_success
```

### Performance Benchmarks

```bash
# Run performance benchmarks
pytest tests/performance/test_benchmarks.py -v

# Run benchmarks and save results
python tests/performance/test_benchmarks.py

# Run with specific markers
pytest tests/performance/ -m "benchmark"
```

## Test Configuration

### Pytest Configuration

The test suite uses pytest with the following configuration (see `pytest.ini`):

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --strict-markers
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    performance: Performance tests
    slow: Slow running tests
    network: Tests requiring network
    mock: Tests using mocks
    real: Tests using real services
```

### Test Fixtures

Test fixtures are automatically loaded from `conftest.py` and provide:

- Application instances
- Mock configurations
- Test data builders
- Performance measurement utilities

## Test Data and Scenarios

### Test Scenarios

The test suite includes several predefined scenarios:

1. **Single Currency**: Tests with one cryptocurrency
2. **Multiple Currencies**: Tests with multiple cryptocurrencies
3. **High Volume**: Performance tests with large datasets
4. **Error Conditions**: Tests for error handling and edge cases

### Data Generation

Test data is generated using the `TestDataGenerator` class, which provides:

- Realistic cryptocurrency configurations
- Valid and invalid addresses
- Transaction and block data
- UTXO sets

## Performance Testing

### Benchmark Categories

Performance benchmarks measure:

1. **Execution Time**: How long operations take
2. **Memory Usage**: Memory consumption patterns
3. **Throughput**: Operations per second under load
4. **Concurrency**: Performance under concurrent access

### Benchmark Results

Benchmark results are saved to `benchmark_results.json` and include:

- Execution times for various operations
- Memory usage statistics
- Throughput measurements
- Performance comparisons

## Best Practices

### Writing Tests

1. **Unit Tests**: Test one thing at a time, use mocks for dependencies
2. **Integration Tests**: Test component interactions, use real or mock services
3. **E2E Tests**: Test complete workflows, use minimal mocking
4. **Performance Tests**: Measure realistic scenarios, track trends

### Test Organization

1. **Group related tests** in appropriate directories
2. **Use descriptive test names** that explain the scenario
3. **Follow naming conventions**: `test_*.py`, `Test*`, `test_*`
4. **Document complex test scenarios** with docstrings

### Mock Usage

1. **Use mocks for external dependencies** (network, databases)
2. **Prefer real implementations** for core logic testing
3. **Configure mocks carefully** to match real behavior
4. **Test both success and failure scenarios**

## Continuous Integration

### Test Execution in CI

The test suite is designed for CI/CD integration:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: pytest --cov=src --cov-report=xml

- name: Run performance benchmarks
  run: pytest tests/performance/ -m benchmark

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

### Quality Gates

The test suite enforces quality gates:

1. **Minimum Coverage**: 80% code coverage required
2. **Performance Thresholds**: Operations must meet performance targets
3. **Error Handling**: All error paths must be tested
4. **Concurrency**: Thread safety must be verified

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `PYTHONPATH` includes the project root
2. **Mock Issues**: Check mock configuration matches real behavior
3. **Performance Variations**: Run benchmarks multiple times for consistent results
4. **Network Tests**: Ensure mock servers are properly configured

### Debugging Tests

```bash
# Run with maximum verbosity
pytest -vvv -s

# Run single test with debugger
pytest tests/unit/test_configuration.py::TestConfigurationManager::test_load_from_environment_success --pdb

# Run with specific logging level
pytest --log-cli-level=DEBUG
```

## Contributing

### Adding New Tests

1. **Choose appropriate test category** (unit/integration/e2e/performance)
2. **Follow existing naming conventions** and structure
3. **Add appropriate test markers** for categorization
4. **Update this README** if new test categories are added
5. **Ensure tests pass** before submitting pull requests

### Test Review Checklist

- [ ] Tests are in the correct directory
- [ ] Test names are descriptive
- [ ] Tests use appropriate mocking
- [ ] Error cases are covered
- [ ] Performance implications are considered
- [ ] Documentation is updated

## Performance Guidelines

### Benchmark Interpretation

1. **Execution Time**: Should be consistent across runs
2. **Memory Usage**: Should not grow unbounded
3. **Throughput**: Should scale with available resources
4. **Concurrency**: Should handle multiple threads safely

### Performance Optimization

1. **Identify bottlenecks** using benchmark results
2. **Profile memory usage** for leaks
3. **Optimize critical paths** first
4. **Measure improvements** with benchmarks

## Test Metrics

### Coverage Metrics

- **Line Coverage**: Percentage of lines executed
- **Branch Coverage**: Percentage of decision points tested
- **Function Coverage**: Percentage of functions called

### Performance Metrics

- **Response Time**: Time to complete operations
- **Throughput**: Operations per second
- **Resource Usage**: CPU and memory consumption
- **Scalability**: Performance under increasing load

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Performance Testing Best Practices](https://en.wikipedia.org/wiki/Software_performance_testing)