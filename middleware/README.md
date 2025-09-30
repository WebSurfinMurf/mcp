# MCP Tool Injection Middleware

Simple stateless proxy that injects MCP tools into OpenAI chat completion requests.

## Architecture

```
Open WebUI → Middleware (port 4001) → LiteLLM (port 4000) → Anthropic/OpenAI
                ↓
        Fetches tools from
        MCP Proxy (port 9090)
```

## How It Works

1. **Startup**: Fetches available tools from MCP proxy once and caches them
2. **Request**: Intercepts `/v1/chat/completions` requests
3. **Injection**: Adds `tools` array if not present
4. **Proxy**: Forwards enriched request to LiteLLM
5. **Response**: Returns LiteLLM's response unchanged

## Features

- ✅ Stateless (tools cached at startup)
- ✅ Streaming support
- ✅ Simple (~150 lines of Python)
- ✅ No MCP protocol handling (LiteLLM does that)
- ✅ Health check endpoint

## Deployment

```bash
cd /home/administrator/projects/mcp/middleware
docker compose up -d
```

## Configuration

Change `LITELLM_URL` or `MCP_PROXY_URL` in `main.py` if needed.

## Endpoints

- `POST /v1/chat/completions` - Main proxy endpoint
- `GET /v1/models` - Models list proxy
- `GET /health` - Health check

## Testing

```bash
# Check health
curl http://localhost:4001/health

# Test with LiteLLM master key
curl -X POST http://localhost:4001/v1/chat/completions \
  -H "Authorization: Bearer sk-litellm-cecca390f610603ff5180ba0ba2674afc8f7689716daf25343de027d10c32404" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5",
    "messages": [{"role": "user", "content": "What databases exist?"}]
  }'
```

## Open WebUI Integration

Update Open WebUI to point to middleware instead of LiteLLM directly:

```env
# /home/administrator/secrets/open-webui.env
OPENAI_API_BASE_URL=http://mcp-middleware:8080/v1
```

Then restart Open WebUI.

## Logs

```bash
docker logs mcp-middleware --follow
```