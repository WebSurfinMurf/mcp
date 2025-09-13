# MCP Monitoring Server

## Executive Summary
MCP server that provides Claude Code with programmatic access to the complete monitoring and observability stack. Integrates with Loki for log aggregation/querying and Netdata for real-time system metrics, enabling Claude to analyze logs, detect errors, check service health, and monitor system performance.

## Current Status
- **Status**: ✅ Operational
- **Type**: Node.js MCP Server
- **Transport**: stdio
- **MCP Name**: `monitoring` (renamed from `observability`)
- **Dependencies**: Loki (logs), Netdata (metrics)

## Architecture
```
Claude Code
     ↓ (MCP Protocol)
MCP Monitoring Server
     ├── Loki API (port 3100)
     │   └── LogQL queries for log analysis
     └── Netdata API (port 19999)
         └── Real-time metrics collection
```

## File Locations
- **Project**: `/home/administrator/projects/mcp-monitoring/`
- **Source**: `/home/administrator/projects/mcp-monitoring/src/index.js`
- **Config**: `~/.config/claude/mcp_servers.json` (registered as 'monitoring')
- **Deploy Script**: `/home/administrator/projects/mcp-monitoring/deploy.sh`
- **Package**: `/home/administrator/projects/mcp-monitoring/package.json`

## Available Tools

### 1. search_logs
Query logs using LogQL syntax for powerful filtering and analysis
```javascript
// Example: Find errors in nginx
{
  query: "{container=\"nginx\"} |= \"error\"",
  hours: 24,
  limit: 100
}

// Example: Parse JSON logs
{
  query: "{container=\"traefik\"} | json | status >= 500",
  hours: 1,
  limit: 50
}
```

### 2. get_recent_errors
Find recent error-level logs across all containers
```javascript
// All errors in last hour
{
  hours: 1
}

// Errors from specific container
{
  hours: 2,
  container: "postgres"
}
```

### 3. get_container_logs
Get logs for a specific container with optional filtering
```javascript
{
  container_name: "grafana",
  hours: 0.5,
  filter: "level=error"  // optional text filter
}
```

### 4. get_system_metrics
Retrieve system metrics from Netdata
```javascript
{
  charts: ["system.cpu", "system.ram", "disk.util"],
  after: 300  // last 5 minutes (in seconds)
}
```

### 5. check_service_health
Comprehensive health check combining logs and metrics
```javascript
{
  service_name: "postgres",
  check_errors: true,    // check for recent errors
  check_restarts: true   // check for container restarts
}
```

## Available Resources
- **logs://recent** - Stream of recent log entries from all containers
- **metrics://current** - Current system metrics snapshot

## Common Operations

### Deploy/Update Server
```bash
cd /home/administrator/projects/mcp-monitoring && ./deploy.sh
```

### Test Server Functionality
```bash
cd /home/administrator/projects/mcp-monitoring && npm test
```

### Manual Testing
```bash
# Start server manually
node /home/administrator/projects/mcp-monitoring/src/index.js

# Test tool listing
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | \
  node /home/administrator/projects/mcp-monitoring/src/index.js
```

### Verify Configuration
```bash
# Check MCP registration
jq '.mcpServers.monitoring' ~/.config/claude/mcp_servers.json

# Test Loki connectivity
curl -s http://localhost:3100/ready

# Test Netdata connectivity
curl -s http://localhost:19999/api/v1/info | jq .
```

## LogQL Query Examples

### Basic Queries
```logql
# All logs from a container
{container="grafana"}

# Logs with specific text
{container="nginx"} |= "404"

# Case-insensitive error search
{container=~".*"} |~ "(?i)error"

# Exclude certain logs
{container="traefik"} != "HealthCheck"
```

### Advanced Queries
```logql
# Parse JSON and filter
{container="loki"} | json | level="error"

# Extract and format fields
{container="postgres"} | regexp "duration: (?P<duration>[0-9.]+)" | line_format "Query took {{.duration}}ms"

# Rate calculation
rate({container="nginx"} |= "error" [5m])

# Count by level
sum by (level) (rate({container="grafana"} | json | __error__="" [5m]))
```

## Netdata Metrics Available

### System Metrics
- `system.cpu` - CPU utilization
- `system.ram` - Memory usage
- `system.io` - Disk I/O
- `system.net` - Network traffic
- `system.processes` - Process statistics

### Container Metrics
- `cgroup_*.cpu` - Per-container CPU
- `cgroup_*.mem` - Per-container memory
- `cgroup_*.net` - Per-container network

### Application Metrics
- `postgres.*` - PostgreSQL statistics
- `redis.*` - Redis metrics
- `nginx.*` - Web server metrics

## Integration with Monitoring Stack

### Dependencies
1. **Loki** (Log Aggregation)
   - URL: http://localhost:3100
   - Stores logs from all containers
   - 30-day retention policy
   - LogQL query language

2. **Netdata** (Metrics Collection)
   - URL: http://localhost:19999
   - Real-time system metrics
   - Per-second granularity
   - Exposed on localhost only (security)

3. **Promtail** (Log Shipping)
   - Collects logs from containers
   - Parses and labels logs
   - Ships to Loki

## Troubleshooting

### Issue: Cannot connect to Loki
```bash
# Check if Loki is running
docker ps | grep loki

# Verify Loki is ready
curl http://localhost:3100/ready

# Check Loki logs
docker logs loki --tail 50

# Test query
curl -G -s "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={container="loki"}' | jq .
```

### Issue: Cannot connect to Netdata
```bash
# Check if Netdata is running
docker ps | grep netdata

# Verify port binding
netstat -tlnp | grep 19999

# Test API access
curl http://localhost:19999/api/v1/info

# Check Netdata logs
docker logs netdata --tail 50
```

### Issue: MCP not recognized by Claude
```bash
# Restart Claude Code after configuration changes
# Then verify configuration
jq '.mcpServers.monitoring' ~/.config/claude/mcp_servers.json

# Check Node.js version (needs >= 18)
node --version

# Test server directly
cd /home/administrator/projects/mcp-monitoring
npm test
```

### Issue: No logs returned
- Check Promtail is running and collecting logs
- Verify container names in queries
- Check time range (default is 24 hours)
- Ensure Loki has data: `curl http://localhost:3100/loki/api/v1/labels`

## Performance Considerations
- **Query Limits**: Default 100 results per query
- **Time Range**: Default 24 hours lookback
- **Rate Limits**: Loki has built-in rate limiting
- **Memory Usage**: Large queries can consume significant memory

## Security Notes
- Netdata bound to localhost only (127.0.0.1:19999)
- No authentication on local APIs (secured by network)
- MCP server runs with user privileges
- Read-only access to monitoring data

## Recent Changes
- **2025-09-01**: Initial deployment as mcp-observability
- **2025-09-01**: Fixed Netdata connection (added port binding)
- **2025-09-01**: Renamed to mcp-monitoring (better reflects dual purpose)

## Future Enhancements
- [ ] Add Prometheus metrics support
- [ ] Implement alert querying from Alertmanager
- [ ] Add trace data from Jaeger/Tempo
- [ ] Support for custom dashboards
- [ ] Metric aggregation functions
- [ ] Log pattern detection

## Related Documentation
- Loki: `/home/administrator/projects/loki/CLAUDE.md`
- Netdata: `/home/administrator/projects/netdata/CLAUDE.md`
- Promtail: `/home/administrator/projects/promtail/CLAUDE.md`
- Grafana: `/home/administrator/projects/grafana/CLAUDE.md`

---
*Last Updated: 2025-09-01 - Renamed from mcp-observability to mcp-monitoring*