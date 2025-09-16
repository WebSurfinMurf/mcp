# MCP Network Configuration Changes - 2025-09-16

**WARNING**: These changes replaced `localhost` references with Docker service names. If services were working before, these changes may break connectivity.

## Files Modified

### 1. `/home/administrator/projects/mcp/server/claude-code-bridge.py`
**Status**: ✅ **CORRECT CHANGE** - This was the original issue
```diff
- MCP_SERVER_URL = "http://localhost:8001"
+ MCP_SERVER_URL = "http://mcp.linuxserver.lan:8001"
```
**Rationale**: Bridge script runs on host, needs to reach container via linuxserver.lan

### 2. `/home/administrator/projects/mcp/monitoring/src/index.js`
**Status**: ⚠️ **POTENTIALLY BREAKING** - Changed localhost to Docker service names
```diff
- const LOKI_URL = process.env.LOKI_URL || 'http://localhost:3100';
- const NETDATA_URL = process.env.NETDATA_URL || 'http://localhost:19999';
+ const LOKI_URL = process.env.LOKI_URL || 'http://loki:3100';
+ const NETDATA_URL = process.env.NETDATA_URL || 'http://netdata:19999';
```
**Risk**: If monitoring service runs on host (not in Docker), this will break

### 3. `/home/administrator/projects/mcp/monitoring/deploy.sh`
**Status**: ⚠️ **POTENTIALLY BREAKING**
```diff
- "LOKI_URL": "http://localhost:3100",
- "NETDATA_URL": "http://localhost:19999",
+ "LOKI_URL": "http://loki:3100",
+ "NETDATA_URL": "http://netdata:19999",
```

### 4. `/home/administrator/projects/mcp/monitoring/test/test.js`
**Status**: ⚠️ **POTENTIALLY BREAKING**
```diff
- const response = await axios.get('http://localhost:3100/ready');
+ const response = await axios.get('http://loki:3100/ready');
- const response = await axios.get('http://localhost:19999/api/v1/info');
+ const response = await axios.get('http://netdata:19999/api/v1/info');
```

### 5. `/home/administrator/projects/mcp/minio/mcp-minio-server.py`
**Status**: ⚠️ **POTENTIALLY BREAKING**
```diff
- endpoint = os.environ.get('MINIO_ENDPOINT', 'http://localhost:9000')
+ endpoint = os.environ.get('MINIO_ENDPOINT', 'http://minio:9000')
```
**Risk**: If MinIO MCP server runs on host, this will break

### 6. `/home/administrator/projects/mcp/server/deploy-microservices.sh`
**Status**: ✅ **CORRECT CHANGE** - Host script accessing container
```diff
- if curl -f -s http://localhost:8000/health > /dev/null; then
+ if curl -f -s http://mcp.linuxserver.lan:8001/health > /dev/null; then
- echo -e "📊 API Documentation: http://localhost:8000/docs"
+ echo -e "📊 API Documentation: http://mcp.linuxserver.lan:8001/docs"
```

### 7. `/home/administrator/projects/mcp/server/deploy.sh`
**Status**: ✅ **CORRECT CHANGE** - Host script accessing container
```diff
- if timeout 30 bash -c 'until curl -sf http://localhost:8000/health > /dev/null; do sleep 2; done'; then
+ if timeout 30 bash -c 'until curl -sf http://mcp.linuxserver.lan:8001/health > /dev/null; do sleep 2; done'; then
- health_info=$(curl -s http://localhost:8000/health | jq -r '.tools_count // "unknown"')
+ health_info=$(curl -s http://mcp.linuxserver.lan:8001/health | jq -r '.tools_count // "unknown"')
```

## Rollback Commands

If services break, use these commands to revert:

### Revert monitoring service:
```bash
cd /home/administrator/projects/mcp/monitoring
git checkout HEAD -- src/index.js deploy.sh test/test.js
```

### Revert MinIO service:
```bash
cd /home/administrator/projects/mcp/minio
git checkout HEAD -- mcp-minio-server.py
```

### Manual revert if git unavailable:

#### monitoring/src/index.js:
```bash
sed -i 's|http://loki:3100|http://localhost:3100|g' /home/administrator/projects/mcp/monitoring/src/index.js
sed -i 's|http://netdata:19999|http://localhost:19999|g' /home/administrator/projects/mcp/monitoring/src/index.js
```

#### monitoring/deploy.sh:
```bash
sed -i 's|http://loki:3100|http://localhost:3100|g' /home/administrator/projects/mcp/monitoring/deploy.sh
sed -i 's|http://netdata:19999|http://localhost:19999|g' /home/administrator/projects/mcp/monitoring/deploy.sh
```

#### minio/mcp-minio-server.py:
```bash
sed -i 's|http://minio:9000|http://localhost:9000|g' /home/administrator/projects/mcp/minio/mcp-minio-server.py
```

## Analysis of Changes

### ✅ Correct Changes (Should Keep):
- `claude-code-bridge.py` → `linuxserver.lan:8001` (bridge on host to container)
- Deploy scripts → `linuxserver.lan:8001` (host scripts to container)

### ⚠️ Questionable Changes (May Need Revert):
- Monitoring service URLs → Docker service names
- MinIO server endpoint → Docker service name

### 🔍 Key Questions to Test:
1. **Where does monitoring service run?** Host or Docker?
2. **Where does MinIO MCP server run?** Host or Docker?
3. **Are these services in same Docker network as loki/netdata/minio?**

## Testing Plan

### Test monitoring service:
```bash
cd /home/administrator/projects/mcp/monitoring
npm test
```

### Test MinIO MCP service:
```bash
# Test MinIO tools via MCP
curl -X POST http://mcp.linuxserver.lan:8001/tools/minio_list_objects \
  -H "Content-Type: application/json" \
  -d '{"input": {"bucket_name": "mcp-storage"}}'
```

### Test Claude Code MCP tools:
Use Claude Code to test n8n, monitoring, and MinIO tools

## ACTUAL RESULTS & REVERTS APPLIED

### ✅ REVERTED: Monitoring Service (CONFIRMED BROKEN)
**Status**: ❌ **BROKE - REVERTED TO LOCALHOST**
- Monitoring service runs on HOST, not in Docker
- Cannot resolve Docker hostnames `loki`, `netdata`
- **REVERTED ALL** monitoring files back to `localhost:3100/19999`
- **Test Result**: ✅ Works after revert

### ✅ KEPT: MinIO Service
**Status**: ✅ **WORKS WITH DOCKER HOSTNAMES**
- MinIO MCP tools still functional after change to `minio:9000`
- Apparently MinIO MCP server runs in context where it can resolve Docker hostnames
- **Test Result**: ✅ `minio_list_objects` working correctly

### ✅ KEPT: Deploy Scripts
**Status**: ✅ **CORRECT - HOST TO CONTAINER ACCESS**
- Deploy scripts run on host, correctly use `linuxserver.lan:8001`

### ✅ KEPT: Claude Code Bridge
**Status**: ✅ **CORRECT - ORIGINAL ISSUE FIXED**
- Bridge runs on host, correctly uses `linuxserver.lan:8001`

## FINAL WORKING CONFIGURATION

### Files Successfully Updated (KEEP):
- ✅ `server/claude-code-bridge.py` → `linuxserver.lan:8001`
- ✅ `server/deploy-microservices.sh` → `linuxserver.lan:8001`
- ✅ `server/deploy.sh` → `linuxserver.lan:8001`
- ✅ `minio/mcp-minio-server.py` → `minio:9000` (works!)

### Files Reverted to localhost (WORKING):
- ✅ `monitoring/src/index.js` → `localhost:3100/19999`
- ✅ `monitoring/deploy.sh` → `localhost:3100/19999`
- ✅ `monitoring/test/test.js` → `localhost:3100/19999`

## LESSON LEARNED

**Rule**: Only change `localhost` to `linuxserver.lan` when:
1. Script/service runs on HOST
2. Needs to access Docker CONTAINER
3. Uses EXPOSED port (like 8001)

**Keep localhost when**:
1. Service runs on HOST
2. Accessing OTHER containers via port mapping
3. Health checks inside containers (self-checks)

---
*Created: 2025-09-16*
*Purpose: Track network configuration changes for easy rollback if needed*