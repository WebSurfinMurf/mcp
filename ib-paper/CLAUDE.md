# MCP IB Paper Trading Server

## Overview
MCP server for Interactive Brokers paper trading with gateway control. Used by websurfinmurf/stocktrader environment.

## Quick Reference
| Property | Value |
|----------|-------|
| Container | mcp-ib-paper |
| Gateway | mcp-ib-gateway-paper |
| HTTP Port | 48012 |
| Gateway Ports | 14001 (live), 14002 (paper), 15900 (VNC) |
| Network | mcp-ib-paper-net |
| Owner | websurfinmurf |

## Configuration
- **Trading Mode**: Paper (always)
- **IB Port**: 4004 (paper socat)
- **Client ID Base**: 1
- **Pool Size**: 3 workers (configurable via IB_POOL_SIZE)
- **Health Check**: Every 30s

## Critical Requirement: VNC API Settings

**The "Allow connections from localhost only" checkbox MUST be UNCHECKED in IB Gateway API Settings for the MCP workers to connect.**

### Why This Happens
- IB Gateway stores API settings in an **encrypted** `ibg.xml` file (IBGZENC format)
- This file is only written when Gateway **closes properly** (via UI exit, not Docker stop)
- Docker stop/restart does NOT trigger a proper save - settings reset
- The socat proxy (4004 → 4002) doesn't help because the API handshake itself is rejected

### When Manual Intervention is Needed
- After `deploy.sh` or Docker restart (unless previously exited via VNC)
- When health shows `api_ready` but `ib_connected: false`
- When workers show high `consecutive_failures` or `restart_count`

**Good news:** Once configured and exited gracefully via VNC, settings persist through subsequent `docker start` commands.

### How to Fix via VNC
1. Connect to VNC: `linuxserver.lan:15900` (password in secrets)
2. Go to: **Configure → Settings → API → Settings**
3. **UNCHECK** "Allow connections from localhost only"
4. Set Socket port: `4002`
5. Click **Apply**
6. Verify with: `curl http://localhost:48012/health`

If this setting is checked, API connections will timeout even with 127.0.0.1 in Trusted IPs.

## Custom Config Files
Located in `./config/`:
- `config.ini.tmpl` - IBC config with `OverrideTwsApiPort=4002`
- `run_socat.sh` - socat forwarding 4004 → 127.0.0.1:4002

## Secrets
Location: `$HOME/projects/secrets/mcp-ib-paper.env`

## Data Persistence
**Settings CAN persist** if IB Gateway is exited gracefully via VNC (File → Exit or close button). Docker stop/restart does NOT save settings.

### To Persist API Settings:
1. Configure via VNC (uncheck "Allow connections from localhost only")
2. Exit IB Gateway through the **UI** (not Docker stop)
3. Restart container - settings will persist

**Note:** The Jts directory cannot be mounted as a volume (breaks required templates). Settings are saved internally when Gateway exits gracefully.

---

## API Endpoints

### MCP Protocol
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp` | POST | JSON-RPC MCP protocol endpoint |
| `/health` | GET | Health check with pool/IB status + options client |
| `/restart-workers` | POST | Force restart all worker processes |

### Options Data (via OptionsClient)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/options/quote/{symbol}` | GET | Options market data snapshot |
| `/options/expirations/{symbol}` | GET | Expiration dates via `reqSecDefOptParams` |
| `/options/chain/{symbol}/{expiration}` | GET | Full chain with Greeks |

### Gateway Control
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/gateway/status` | GET | Check gateway connection status |
| `/gateway/logout` | POST | Stop gateway (free session for TWS) |
| `/gateway/login` | POST | Start gateway (auto-authenticates) |
| `/gateway/reconnect` | POST | Full restart of gateway |
| `/gateway/ensure-ready` | POST | Check connection, auto-reconnect if needed (blocks until ready) |

---

## Gateway Control API

### GET /gateway/status
Check IB Gateway connection status.

**Response:**
```json
{
  "status": "connected",
  "container_running": true,
  "api_port_open": true,
  "ib_connected": true,
  "gateway_container": "mcp-ib-gateway-paper",
  "api_host": "ibgateway-paper",
  "api_port": "4004"
}
```

**Status Values:**
| Status | Meaning |
|--------|---------|
| `connected` | Gateway running AND IB authenticated |
| `api_ready` | Gateway running, API port open, not authenticated yet |
| `starting` | Container running but API not ready |
| `disconnected` | Gateway container stopped |

### POST /gateway/logout
Stop gateway container to free IB session for TWS desktop login.

**Response:**
```json
{
  "success": true,
  "message": "Gateway stopped. IB session is now free for TWS.",
  "note": "Use POST /gateway/login to restart the gateway when ready."
}
```

### POST /gateway/login
Start gateway container. Auto-authenticates with saved credentials.

**Response:**
```json
{
  "success": true,
  "message": "Gateway started. Authentication in progress.",
  "note": "Wait 30-60 seconds for gateway to authenticate, then check /gateway/status"
}
```

### POST /gateway/reconnect
Full restart of gateway (stop + start). Use when gateway is stuck.

**Response:**
```json
{
  "success": true,
  "message": "Gateway restart initiated. Workers stopped.",
  "note": "Wait 30-60 seconds for gateway to reconnect, then check /gateway/status"
}
```

### POST /gateway/ensure-ready
Ensure gateway is connected before making requests. **Recommended for client apps.**

- Returns immediately if already connected
- Auto-reconnects and waits if disconnected
- Blocks until ready or timeout (default 90s)

**Response (already connected):**
```json
{
  "ready": true,
  "message": "Gateway already connected",
  "waited": 0
}
```

**Response (reconnected):**
```json
{
  "ready": true,
  "message": "Gateway connected after 45s",
  "waited": 45
}
```

**Client usage example:**
```python
# Call before critical IB operations
response = requests.post("http://localhost:48012/gateway/ensure-ready", timeout=90)
if response.json()["ready"]:
    # Make IB requests
    result = requests.post("http://localhost:48012/mcp", json={...})
```

---

## Health Check API

### GET /health
Returns comprehensive health status including options client.

**Response:**
```json
{
  "status": "healthy",
  "ib_connected": true,
  "options_client_connected": true,
  "service": "ib-paper",
  "ib_host": "ibgateway-paper",
  "ib_port": "4004",
  "circuit_breaker": {
    "state": "closed",
    "failure_count": 0,
    "last_failure_ago": null,
    "recovery_in": null
  },
  "pool": {
    "pool_size": 3,
    "workers_alive": 3,
    "workers_ib_connected": 3,
    "workers_available": 2,
    "workers": [...]
  }
}
```

**Health Status Values:**
| Status | Meaning |
|--------|---------|
| `healthy` | Workers OR options_client connected to IB |
| `degraded` | Containers alive but neither workers nor options_client connected |
| `unhealthy` | No workers or circuit breaker open |

**Note**: `ib_connected` is true if EITHER `options_client_connected` OR workers are connected.

---

## MCP Tools (10 total)

| Tool | Description |
|------|-------------|
| `get_account_summary` | Account info (equity, buying power) |
| `get_positions` | Current portfolio positions |
| `get_historical_data` | Historical price data (OHLCV) |
| `get_contract_details` | Detailed contract specifications |
| `lookup_contract` | Find contracts by symbol |
| `search_contracts` | Search contracts by pattern |
| `ticker_to_conid` | Convert ticker to contract ID |
| `get_fundamental_data` | Company fundamental data |
| `get_historical_news` | Historical news headlines |
| `get_article` | Fetch news article by ID |

---

## Common Commands

```bash
# Deploy
cd /home/administrator/projects/mcp/ib-paper && ./deploy.sh

# Logs
docker logs mcp-ib-paper --tail 50
docker logs mcp-ib-gateway-paper --tail 50

# Health check
curl http://localhost:48012/health

# Gateway status
curl http://localhost:48012/gateway/status

# Gateway logout (for TWS)
curl -X POST http://localhost:48012/gateway/logout

# Gateway login
curl -X POST http://localhost:48012/gateway/login

# Ensure ready (blocks until connected)
curl -X POST http://localhost:48012/gateway/ensure-ready

# Test MCP call
curl -X POST http://localhost:48012/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"get_account_summary","arguments":{}}}'
```

---

## Architecture

```
optionsearch-api / stocktrader-model
      │ (HTTP)
      ▼
mcp-ib-paper:8000
  ├── /mcp → IBWorkerPool (3 workers via ib_mcp)
  ├── /options/* → OptionsClient (ib_async 2.1.0)
  ├── /health → Pool + options_client status
  └── /gateway/* → Docker control
      │
      ├─── STDIO ───▶ ib_mcp.server subprocess
      │                    │
      └─── direct ──▶ OptionsClient (ib_async)
                           │
                           ▼
                    socat (port 4004 → 127.0.0.1:4002)
                           │
                           ▼
                    mcp-ib-gateway-paper
                           │ (HTTPS)
                           ▼
                    Interactive Brokers Cloud
```

### Two Connection Paths
1. **MCP Workers** (`/mcp`): Use `ib_mcp` library via subprocess STDIO - for general IB requests
2. **OptionsClient** (`/options/*`): Use `ib_async` directly - for options data via `reqSecDefOptParams` (avoids throttling)

### Features
- **Process Pool**: 3 workers with unique client IDs
- **Options Client**: Dedicated `ib_async` connection (client ID 99) for options data
- **Circuit Breaker**: Prevents cascading failures (3 failures → 60s cooldown)
- **Health Monitoring**: Background task checks IB connectivity every 30s (staggered 2s between workers)
- **Smart Restart**: Workers only restart after 2+ consecutive failures with exponential backoff (5s→10s→20s→40s→60s max)
- **Auto-Reconnect**: Gateway automatically restarts if BOTH workers AND options_client disconnect for 60s
- **Ensure Ready**: `/gateway/ensure-ready` endpoint for client apps to verify connection
- **Gateway Control**: Docker socket for container management

### Health Check Behavior
- Checks each worker's IB connectivity every 30s (staggered)
- Worker restart only after 2+ consecutive health check failures
- Exponential backoff between restarts prevents restart storms
- `restart_count` tracks attempts, resets only on successful IB connection
- Gateway auto-restart only if BOTH workers AND options_client disconnected for 2 consecutive checks (60s)

---

## Troubleshooting

### Workers Not Connecting (api_ready but ib_connected: false)
**Symptoms:**
- `/health` shows `status: degraded`
- `/gateway/status` shows `api_ready` but `ib_connected: false`
- Workers have high `consecutive_failures` and `restart_count`

**Cause:** "Allow connections from localhost only" is checked in IB Gateway

**Fix:** VNC intervention required (see Critical Requirement section above)

### Gateway Restart Loop
**Symptoms:**
- Gateway keeps restarting
- Workers never stabilize

**Cause:** Auto-reconnect triggers but VNC setting resets

**Fix:**
1. Manually stop auto-reconnect: `curl -X POST http://localhost:48012/gateway/logout`
2. Fix VNC setting
3. Restart: `curl -X POST http://localhost:48012/gateway/login`

### Diagnosing Connection Issues
```bash
# Check worker status
curl -s http://localhost:48012/health | jq '.pool.workers'

# Check gateway status
curl -s http://localhost:48012/gateway/status | jq

# Test IB API connection directly
docker exec mcp-ib-paper python3 -c "
from ib_insync import IB
import asyncio
async def test():
    ib = IB()
    await ib.connectAsync('ibgateway-paper', 4004, clientId=99, timeout=10)
    print(f'Connected! Accounts: {ib.wrapper.accounts}')
asyncio.run(test())
"

# Check if socat is running
docker exec mcp-ib-gateway-paper ps aux | grep socat

# View gateway logs for auth status
docker logs mcp-ib-gateway-paper --tail 50 | grep -i "login\|auth\|api"
```

---

## Known Issues & Lessons Learned

### Volume Mounting Limitation
**Cannot mount `/home/ibgateway/Jts` as a volume** - doing so overwrites required template files (`jts.ini.tmpl`) and causes the container to crash in a restart loop.

### Settings Persistence Matrix
| Action | Settings Persist? | Notes |
|--------|-------------------|-------|
| `docker stop` / `docker restart` | No | SIGTERM doesn't trigger config save |
| `deploy.sh` | No | Recreates container |
| `docker compose up` | No | Recreates container |
| VNC UI Exit (File → Exit) | **Yes** | Triggers proper config save |
| `docker start` after VNC exit | **Yes** | Settings already saved |

### IBC vs UI Settings
IBC automation can set some settings via `config.ini`:
- `OverrideTwsApiPort` - Works
- `ReadOnlyApi` - Works
- **"Allow connections from localhost only"** - NOT controllable via IBC, only via VNC UI

### TCP vs API Connection
- **TCP connect succeeds** even when API fails
- API timeout indicates "localhost only" is checked
- The socat proxy forwards TCP but doesn't bypass the API-level restriction

---

## Related
- **Live Server**: `/home/administrator/projects/mcp/ib-live/`
- **Original Setup**: `/home/administrator/projects/mcp/ib/`
- **Source Code**: `/home/administrator/projects/mcp/ib/src/server.py`

---

## Operational Workflow

### Initial Setup (one-time after deploy)
```bash
# 1. Deploy
./deploy.sh

# 2. Wait for gateway to authenticate (~60s)
sleep 60

# 3. Configure via VNC
#    - Connect to linuxserver.lan:15900
#    - Uncheck "Allow connections from localhost only"
#    - Click Apply

# 4. Exit gracefully via VNC UI (File → Exit)

# 5. Start container (settings now persist)
docker start mcp-ib-gateway-paper
```

### Daily Operations
```bash
# Start (if stopped)
docker start mcp-ib-gateway-paper mcp-ib-paper

# Check health
curl -s http://localhost:48012/health | jq '{status, ib_connected}'

# Stop (preserves settings for next start)
docker stop mcp-ib-gateway-paper mcp-ib-paper
```

### After Code Changes
```bash
# deploy.sh recreates containers - VNC config required again
./deploy.sh
# Then repeat VNC configuration steps
```

---
*Last Updated: 2025-12-11 (options client architecture, health check updates, ib_async 2.1.0)*
