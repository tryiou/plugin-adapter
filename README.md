# Plugin Adapter

A high-performance cryptocurrency adapter service that provides a unified RPC interface for multiple cryptocurrencies using the ElectrumX protocol. This service acts as a bridge between applications and various cryptocurrency networks.

## Architecture Overview

The plugin adapter follows a modular, thread-safe architecture with these key components:

- **Application Server**: HTTP server using aiohttp for handling RPC requests
- **Configuration Manager**: Thread-safe configuration handling for multiple currencies
- **RPC Handlers**: Specialized handlers for different RPC method categories
- **Networking Layer**: Async TCP socket management for ElectrumX communication
- **Heartbeat Manager**: Connection monitoring and health checks

## Supported Currencies

BLOCK, BTC, BCH, LTC, DASH, DOGE, DGB, PIVX, RVN, SYS, TZC, XSN, UNO, PKOIN

## Quick Start

### Environment Setup
Set the `UTXO_PLUGIN_LIST` environment variable with currency configurations:
```bash
export UTXO_PLUGIN_LIST='BLOCK:172.31.8.23,SYS:172.31.10.15'
```

### Docker Deployment
```bash
docker run -d \
  --name plugin-adapter \
  -e UTXO_PLUGIN_LIST='BLOCK:172.31.8.23,SYS:172.31.10.15' \
  -p 5000:5000 \
  blocknetdx/plugin-adapter
```

### Kubernetes Deployment
See the deployment example in the EXR environment section below.

## API Endpoints

### RPC Endpoint
- **POST /** - Handle all RPC methods (getutxos, getrawtransaction, sendrawtransaction, etc.)

### Monitoring Endpoints
- **GET /height** - Get block heights for all configured currencies
- **GET /fees** - Get transaction fees for all configured currencies

### Supported RPC Methods
- `getutxos` - Get unspent transaction outputs
- `getrawtransaction` - Get raw transaction data
- `sendrawtransaction` - Broadcast transactions
- `getblockcount` - Get current block count
- `getblock` - Get block data by hash
- `getblockhash` - Get block hash by height
- `getbalance` - Get address balance
- `gethistory` - Get transaction history
- `ping` - Health check

## EXR Environment Deployment

Within the EXR ENV, use this general form:

```yaml
plugin-adapter:
  image: blocknetdx/plugin-adapter
  restart: unless-stopped
#  ports:
#    - "5000:5000"
  environment:
    UTXO_PLUGIN_LIST: 'BLOCK:172.31.8.23,SYS:172.31.10.15'
  stop_signal: SIGINT
  stop_grace_period: 5m
  depends_on:
    - utxo-plugin-BLOCK
    - utxo-plugin-SYS
  logging:
    driver: "json-file"
    options:
      max-size: "2m"
      max-file: "10"
  networks:
    backend:
      ipv4_address: 172.31.10.28
```

The `UTXO_PLUGIN_LIST` environment variable contains a comma-separated list of currency configurations in the format `CURRENCY:HOST,CURRENCY:HOST`.
