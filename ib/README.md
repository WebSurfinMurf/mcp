# Interactive Brokers MCP Server

Model Context Protocol (MCP) server for Interactive Brokers, enabling AI assistants to access IB market data and account information.

## Features

- **MCP Integration**: Access IB data through standardized Model Context Protocol
- **IB Gateway**: Integrated IB Gateway for API connectivity
- **Market Data**: Historical data, real-time quotes, news
- **Account Access**: Portfolio, positions, account summary
- **Contract Lookup**: Symbol resolution and contract details
- **AI-Ready**: Works with Claude Code and other MCP-compatible tools

## Architecture

This setup includes:
1. **IB Gateway**: Handles connection to Interactive Brokers
2. **MCP Server**: Exposes IB data via MCP protocol

## Prerequisites

- Docker and Docker Compose
- Interactive Brokers account with API access enabled
- Claude Code or other MCP-compatible client

## Setup

1. **Copy environment file:**
   ```bash
   cp .env.example /home/administrator/projects/secrets/mcp-ib.env
   ```

2. **Configure credentials:**
   Edit `/home/administrator/projects/secrets/mcp-ib.env` and set your IB credentials:
   ```bash
   IB_USERNAME=your_username
   IB_PASSWORD=your_password
   TRADING_MODE=paper
   IB_READONLY=true
   ```

3. **Deploy:**
   ```bash
   ./deploy.sh
   ```

## MCP Integration

### Add to Claude Code

```bash
codex mcp add mcp-ib docker exec -i mcp-ib python -m ib_mcp.server --host ibgateway --port 4002
```

### MCP Configuration

The `mcp-config.json` file contains the MCP server configuration:

```json
{
  "mcpServers": {
    "mcp-ib": {
      "command": "docker",
      "args": ["exec", "-i", "mcp-ib", "python", "-m", "ib_mcp.server", ...]
    }
  }
}
```

## Available MCP Tools

The MCP server provides these tools:

### Market Data
- `lookup_contract`: Find contract details by symbol
- `ticker_to_conid`: Convert ticker to contract ID
- `get_historical_data`: Fetch historical price data
- `get_news`: Get latest market news
- `get_historical_news`: Fetch historical news articles

### Account & Portfolio
- `get_portfolio`: View current positions
- `get_account_summary`: Account balance and metrics
- `get_fundamental_data`: Company fundamental data

## Ports

- `14001`: IB Gateway live trading (external access)
- `14002`: IB Gateway paper trading (external access)
- `15900`: VNC GUI access
- `3000`: MCP server (stdio via Docker)
- Internal: `4001/4002` - IB Gateway ports accessible within Docker network

## Usage Examples

### With Claude Code

Once configured, you can ask Claude:

```
"What's my current portfolio?"
"Get historical data for AAPL from last month"
"Look up the contract for SPY options"
"Show me account summary"
```

### Direct Docker Access

```bash
# Interactive session
docker exec -it mcp-ib python -m ib_mcp.server --host ibgateway --port 4002

# View logs
docker compose logs -f mcp-ib
```

## Configuration

### Environment Variables

**IB Gateway:**
- `IB_USERNAME`: IB account username
- `IB_PASSWORD`: IB account password
- `TRADING_MODE`: `paper` or `live`
- `READ_ONLY_API`: Enable read-only mode
- `VNC_SERVER_PASSWORD`: VNC password for GUI access

**MCP Server:**
- `IB_HOST`: Gateway hostname (default: `ibgateway`)
- `IB_PORT`: Gateway port (default: `4002`)
- `IB_CLIENT_ID`: Client ID for connection (default: `1`)
- `IB_READONLY`: Read-only mode (default: `true`)

## Management

### View logs
```bash
docker compose logs -f
```

### Restart services
```bash
docker compose restart
```

### Stop services
```bash
docker compose down
```

### Rebuild MCP container
```bash
docker compose build mcp-ib
docker compose up -d
```

## Security

⚠️ **Important:**

1. **Read-only mode**: Default configuration is read-only (`IB_READONLY=true`)
2. **Credentials**: Never commit `.env` to version control
3. **Network isolation**: Services use internal Docker networks
4. **API access**: Enable only required API permissions in IB account
5. **2FA**: Enable two-factor authentication on IB account

## Troubleshooting

### MCP Connection Issues
```bash
# Check if containers are running
docker compose ps

# View MCP server logs
docker compose logs mcp-ib

# Test IB Gateway connection
docker exec -it mcp-ib python -c "from ib_insync import IB; ib = IB(); print(ib.connect('ibgateway', 4002, clientId=1))"
```

### IB Gateway Issues
```bash
# Check gateway logs
docker compose logs ibgateway

# Access VNC GUI
# Connect to localhost:5900 with VNC client
```

### Authentication Failures
- Verify credentials in `.env`
- Check IB account API access settings
- Review 2FA configuration
- Check `TWOFA_TIMEOUT_ACTION` setting

## Development

### Custom MCP Tools

To add custom tools, modify the Dockerfile and add your Python code:

```python
from ib_mcp import create_server

server = create_server()

@server.tool()
async def my_custom_tool(symbol: str):
    """Your custom tool description"""
    # Implementation
    pass
```

## References

- [MCP Documentation](https://github.com/modelcontextprotocol)
- [mcp-ib GitHub](https://github.com/Hellek1/mcp-ib)
- [IB API Docs](https://interactivebrokers.github.io/tws-api/)
- [ib-insync Documentation](https://ib-insync.readthedocs.io/)

## Related Projects

- `ibgateway/`: Standalone IB Gateway setup
- Other MCP implementations:
  - [IB_MCP](https://github.com/rcontesti/IB_MCP) - Client Portal Gateway based
  - [IBKR-MCP-Server](https://github.com/xiao81/IBKR-MCP-Server) - TWS API based
