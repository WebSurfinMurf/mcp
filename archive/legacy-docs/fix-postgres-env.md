# PostgreSQL MCP Environment Variable Issue

## Problem
The postgres MCP is failing with:
```
ValueError: Error: No database URL provided. Please specify via 'DATABASE_URI' environment variable
```

## Root Cause
The proxy is passing `${POSTGRES_PASSWORD}` literally instead of expanding it. The proxy container has the environment variable set:
- `POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-Pass123qp}`

But when it spawns the postgres subprocess, it's not expanding the variable in the command:
```
docker run --rm -i --network postgres-net -e PGPASSWORD=${POSTGRES_PASSWORD} ...
```

## Solutions

### Option 1: Use DATABASE_URI directly
Instead of multiple PG* variables, use the single DATABASE_URI that postgres-mcp expects:

```json
{
  "postgres": {
    "command": "docker",
    "args": [
      "run", "--rm", "-i",
      "--network", "postgres-net",
      "-e", "DATABASE_URI=postgresql://admin:Pass123qp@postgres:5432/postgres",
      "crystaldba/postgres-mcp"
    ]
  }
}
```

### Option 2: Fix environment variable expansion
The proxy needs to expand environment variables before executing. This requires modifying the proxy code or configuration to properly substitute variables.

### Option 3: Use docker exec on existing container
Instead of spawning new containers, exec into the already-running mcp-postgres container:

```json
{
  "postgres": {
    "command": "docker",
    "args": [
      "exec", "-i",
      "mcp-postgres",
      "postgres-mcp"
    ]
  }
}
```

## Recommendation
Use **Option 1** for immediate fix - hardcode the DATABASE_URI with the known password. This eliminates the variable expansion issue entirely.

## Container Structure Issues

Current state:
- **mcp-proxy-main** (port 8500) - Broken due to postgres env issue
- **mcp-proxy-sse** (port 8585) - Partially working (3/5 services)
- **Unnamed containers** - Created by proxy spawning docker run without --name

Recommended approach:
1. Stop and remove mcp-proxy-main (it's broken)
2. Keep mcp-proxy-sse as the working foundation
3. Fix its configuration to include all 5 services properly
4. Add --name parameters to prevent unnamed containers