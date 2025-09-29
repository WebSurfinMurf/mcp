# MCP Filesystem SSE Wrapper

## Setup Steps (host)
```
cd /home/administrator/projects/mcp/filesystem-sse
npm install
```

Update environment variables as needed:
```
export MCP_SSE_PORT=9073
```

## Running locally
```
npm start
```

## Docker build (placeholder)
```
docker network create mcp-sse-net  # one-time
docker-compose build
docker-compose up -d
```
