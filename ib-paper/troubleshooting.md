# IB Gateway Paper Trading - Troubleshooting

## Issue RESOLVED (2025-12-04)

**Problem**: MCP workers could not connect to IB Gateway API - connections timeout.

**Solution**: Uncheck "Allow connections from localhost only" in API Settings via VNC.

The "localhost only" restriction was blocking all API connections even with 127.0.0.1 in Trusted IPs. Once unchecked, all 3 workers connected successfully.

---

## Previous Issue (2025-12-04)

**Problem**: MCP workers cannot connect to IB Gateway API - connections timeout.

### Root Cause Analysis

After extensive investigation on 2025-12-04:
1. **Login DOES complete** - IBC logs show "Login has completed" and "Configuration tasks completed"
2. **Gateway IS authenticated** - VNC shows green "connected" status for IB servers
3. **API socket IS listening** - Port 4002 shows as LISTEN state on IPv6 (`::`)
4. **But connections TIMEOUT** - TCP SYN packets sent but no SYN-ACK received
5. **IBC config updated** - `OverrideTwsApiPort=4002` now set correctly
6. **socat uses IPv6** - Forwarding 4004 → [::1]:4002

The API socket appears to be open but not accepting connections. This could indicate:
- The Java application has opened the socket but isn't calling accept()
- Internal IB Gateway API server is not fully initialized
- Manual UI interaction required to activate the API server

### Current Status

```
[PASS] Gateway container running
[PASS] MCP container running
[PASS] Port 4004 (socat) listening
[PASS] Port 4002 shows LISTEN in /proc/net/tcp6
[PASS] IBC configured OverrideTwsApiPort=4002
[PASS] IBC says "TWS API socket port is already set to 4002"
[FAIL] TCP connections to [::1]:4002 timeout
[FAIL] MCP workers cannot connect
```

### Architecture
```
stocktrader-model
      │ (HTTP)
      ▼
mcp-ib-paper:8000 ──────→ ibgateway-paper:4004
  ├── /mcp                    │
  ├── /health                 ▼
  └── /gateway/*          socat (listening on 4004)
                              │
                              ▼
                    [::1]:4002 ← LISTENING but connections TIMEOUT
                              │
                              ▼
                    IB Gateway API (not accepting connections)
```

### Configuration Files Changed

Custom config files mounted:
- `./config/config.ini.tmpl` - IBC config with `OverrideTwsApiPort=4002`
- `./config/run_socat.sh` - socat using IPv6 [::1] instead of 127.0.0.1

### What We've Tried

1. ✓ Fresh reinstall of IB Gateway image
2. ✓ Set `OverrideTwsApiPort=4002` in IBC config
3. ✓ Set `CommandServerPort=7462` for IBC commands
4. ✓ Set `AcceptIncomingConnectionAction=accept`
5. ✓ Fixed socat to use IPv6 [::1]:4002
6. ✓ Verified socket shows as LISTEN in /proc/net/tcp6
7. ✗ Connections still timeout (SYN sent, no SYN-ACK received)

### Required: Manual VNC Intervention

The API socket may need manual activation via VNC:

1. Connect to VNC: `linuxserver.lan:15900` (password: Qwer-0987on)
2. Go to: Configure → Settings → API → Settings
3. Try: Toggle "Allow connections from localhost only" OFF then ON
4. Click Apply
5. Restart the gateway container: `docker compose restart mcp-ib-gateway-paper`

---

## Diagnostic Scripts

Located in `./scripts/`:

### diagnose.sh
Full diagnostic check of all components.
```bash
./scripts/diagnose.sh
```

### test-mcp-tools.sh
Test MCP tool functionality.
```bash
./scripts/test-mcp-tools.sh [port]
```

### check-api-socket.sh
Monitor API socket status.
```bash
./scripts/check-api-socket.sh [container] [expected_port] [--monitor]
```

---

## Solution: Fresh Reinstall

Since the config files (encrypted ibg.xml) may be corrupted or in a bad state, a fresh reinstall is recommended:

### Step 1: Stop and Remove Current Containers
```bash
cd /home/administrator/projects/mcp/ib-paper
docker compose down
docker volume rm mcp-ib-paper_gateway-data 2>/dev/null  # If using volumes
```

### Step 2: Remove Gateway Image Cache
```bash
docker rmi ghcr.io/gnzsnz/ib-gateway:latest
```

### Step 3: Pull Fresh Image
```bash
docker pull ghcr.io/gnzsnz/ib-gateway:latest
```

### Step 4: Start Fresh
```bash
set -a && source $HOME/projects/secrets/mcp-ib-paper.env && set +a
docker compose up -d
```

### Step 5: Monitor Login and Enable API via VNC
```bash
# Watch logs
docker logs -f mcp-ib-gateway-paper

# Once login completes, connect via VNC:
# Host: linuxserver.lan:15900
# Password: Qwer-0987on
#
# Go to: Configure → Settings → API → Settings
# - Check "Enable ActiveX and Socket Clients" if visible
# - Set Socket port to 4002
# - Click Apply
```

### Step 6: Verify
```bash
./scripts/diagnose.sh
```

---

## VNC Access

```
Host: linuxserver.lan:15900
Password: Qwer-0987on
```

### API Settings Location
Configure → Settings → API → Settings

### Expected Settings
- Socket port: 4002
- Read-Only API: unchecked
- Allow connections from localhost only: checked
- Trusted IPs: 127.0.0.1

---

## Useful Commands

```bash
# Full diagnostics
./scripts/diagnose.sh

# Check API port listening (IPv6 - IB Gateway uses IPv6)
docker exec mcp-ib-gateway-paper sh -c 'cat /proc/net/tcp6' | \
  awk 'NR>1 {split($2,a,":"); if(a[2]=="0FA2") print "4002 LISTENING on IPv6"}'

# Test connection to API port
docker exec mcp-ib-gateway-paper sh -c 'echo "" | socat -t 2 - TCP6:[::1]:4002 2>&1'

# Check socat
docker exec mcp-ib-gateway-paper ps aux | grep socat

# Gateway logs (IBC messages)
docker logs mcp-ib-gateway-paper 2>&1 | grep -E 'IBC:|Login|Configuration'

# MCP health
curl -s http://localhost:48012/health | jq .

# Gateway status
curl -s http://localhost:48012/gateway/status | jq .

# Test MCP call
curl -X POST http://localhost:48012/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"get_account_summary","arguments":{}}}'
```

---

## Port Configuration Reference

| Mode | socat Port | Internal API Port | VNC Port |
|------|------------|-------------------|----------|
| Paper | 4004 | 4002 | 15900 |
| Live | 4003 | 4001 | 15901 |

---

## Previous Issues (Resolved)

### Port Mismatch (2025-12-02)
**Problem**: socat was forwarding to wrong port
- jts.ini: LocalServerPort=4000
- UI: Socket port=4002
- socat: 4004 → 4000 (wrong!)

**Fix**: Changed `API_PORT=4002` in docker-compose.yml to make socat forward to 4002.

---

*Last Updated: 2025-12-04*
