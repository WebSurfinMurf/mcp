# Custom HTTP-Native Playwright MCP Service

**Expert-Recommended Solution**: A production-ready, HTTP-native Playwright service designed specifically for the MCP microservice orchestrator pattern.

## Overview

This service replaces Microsoft's `playwright-mcp` which had fundamental limitations for persistent communication. Built with the expert-validated "AI Gateway with Adapters" pattern, it provides:

- **Persistent Browser Management**: Single browser instance with isolated contexts per request
- **HTTP REST API**: Clean integration with the MCP orchestrator
- **Production-Ready**: Comprehensive error handling, timeouts, and resource management
- **Security-First**: Non-root execution, request isolation, domain validation ready

## Architecture

```
MCP Orchestrator → HTTP Request → Playwright Service → Browser Context → Tool Execution
```

### Key Design Principles

1. **Persistent Browser**: One browser instance serves multiple requests via isolated contexts
2. **Request Isolation**: Each tool execution gets a fresh browser context
3. **Resource Cleanup**: Automatic context cleanup after each request
4. **Error Resilience**: Graceful error handling with detailed logging

## Available Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `navigate` | Navigate to URL and wait for load | `url`, `wait_for_load`, `timeout` |
| `screenshot` | Take page screenshot | `full_page`, `clip`, `format` |
| `click` | Click element by selector | `selector`, `timeout` |
| `fill` | Fill form field with text | `selector`, `value`, `timeout` |
| `evaluate` | Execute JavaScript in page | `script`, `args` |
| `get-content` | Get page or element text content | `selector` |
| `wait-for-selector` | Wait for element to appear | `selector`, `timeout`, `state` |

## API Endpoints

### Service Management
- `GET /health` - Health check and browser status
- `GET /info` - Detailed service information
- `GET /tools` - List all available tools

### Tool Execution
- `POST /tools/{toolName}` - Execute specific tool

### Request Format
```json
{
  "input": {
    "url": "https://example.com",
    "timeout": 30000
  }
}
```

### Response Format
```json
{
  "tool": "navigate",
  "result": {
    "success": true,
    "url": "https://example.com",
    "title": "Example Domain",
    "status": 200
  },
  "requestId": 1757895116572,
  "timestamp": "2025-09-14T22:58:26.030Z",
  "status": "success"
}
```

## Usage Examples

### Navigation
```bash
curl -X POST http://localhost:8080/tools/navigate \
  -H "Content-Type: application/json" \
  -d '{"input": {"url": "https://example.com"}}'
```

### Screenshot
```bash
curl -X POST http://localhost:8080/tools/screenshot \
  -H "Content-Type: application/json" \
  -d '{"input": {"full_page": true}}'
```

### Click Element
```bash
curl -X POST http://localhost:8080/tools/click \
  -H "Content-Type: application/json" \
  -d '{"input": {"selector": "button.submit"}}'
```

## Docker Deployment

### Build
```bash
docker build -t playwright-http-service .
```

### Run Standalone
```bash
docker run -p 8080:8080 --name playwright-service playwright-http-service
```

### Docker Compose Integration
```yaml
playwright-http-service:
  build:
    context: /home/administrator/projects/mcp/playwright-http-service
  container_name: playwright-http-service
  restart: unless-stopped
  ports:
    - "8080:8080"
  environment:
    NODE_ENV: production
    PORT: 8080
  security_opt:
    - seccomp:unconfined  # Required for Chromium
  healthcheck:
    test: ["CMD", "node", "-e", "require('http').get('http://localhost:8080/health', (r) => process.exit(r.statusCode === 200 ? 0 : 1)).on('error', () => process.exit(1))"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 60s
```

## Integration with MCP Orchestrator

### Python Wrapper Tools

```python
@tool
def playwright_navigate(url: str, wait_for_load: bool = True) -> str:
    """Navigate to a URL and wait for page load"""
    try:
        response = requests.post('http://playwright-http-service:8080/tools/navigate',
                               json={'input': {'url': url, 'wait_for_load': wait_for_load}},
                               timeout=60)
        if response.status_code == 200:
            result = response.json()
            return f"Successfully navigated to {result['result']['title']} ({result['result']['url']})"
        else:
            return f"Navigation failed: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def playwright_screenshot(full_page: bool = False) -> str:
    """Take a screenshot of the current page"""
    try:
        response = requests.post('http://playwright-http-service:8080/tools/screenshot',
                               json={'input': {'full_page': full_page}},
                               timeout=60)
        if response.status_code == 200:
            result = response.json()
            return f"Screenshot captured: {result['result']['size']} bytes in {result['result']['format']} format"
        else:
            return f"Screenshot failed: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error: {str(e)}"
```

## Performance Characteristics

- **Browser Startup**: ~2-3 seconds (once per container)
- **Context Creation**: ~50-100ms per request
- **Tool Execution**: Varies by operation + network latency
- **Memory Usage**: ~200-300MB baseline + ~50MB per active context
- **Concurrent Requests**: Supports multiple simultaneous contexts

## Security Features

- **Non-root execution**: Runs as `pwuser`
- **Request isolation**: Each request gets isolated browser context
- **Resource cleanup**: Automatic context disposal prevents memory leaks
- **Timeout protection**: Configurable timeouts prevent runaway operations
- **Domain validation ready**: Framework for implementing domain restrictions

## Monitoring & Logging

- **Structured logging**: Request IDs for tracing
- **Health checks**: Browser status monitoring
- **Error tracking**: Detailed error messages with context
- **Resource monitoring**: Context creation/cleanup logging

## Comparison with Microsoft's Implementation

| Feature | Microsoft playwright-mcp | Custom HTTP Service |
|---------|-------------------------|-------------------|
| **Communication** | stdio (single-use) | HTTP (persistent) |
| **Browser Management** | Spawn per tool call | Persistent with contexts |
| **Performance** | High overhead | Optimized for repeated use |
| **Integration** | Requires adapter | Direct HTTP integration |
| **Reliability** | Exits after tools calls | Robust error handling |
| **Maintainability** | External dependency | Full control |

## Expert Validation

This implementation follows the expert-recommended approach:

> *"Build a Custom, HTTP-Native Playwright MCP Service. This is the professional, long-term solution. It maintains your clean microservice architecture and gives you full control over functionality."*

**Benefits Achieved**:
- ✅ Preserves perfect separation of concerns
- ✅ Resource-intensive browser automation isolated
- ✅ Full control over functionality and performance
- ✅ Leverages proven infrastructure patterns
- ✅ Eliminates dependency on external team's design choices

## Development

### Local Development
```bash
npm install
npm start
```

### Testing
```bash
# Health check
curl http://localhost:8080/health

# Service info
curl http://localhost:8080/info

# Test navigation
curl -X POST http://localhost:8080/tools/navigate \
  -H "Content-Type: application/json" \
  -d '{"input": {"url": "https://httpbin.org/get"}}'
```

---

**Status**: Production-ready replacement for Microsoft's playwright-mcp
**Architecture**: Expert-validated microservice pattern
**Integration**: Ready for MCP orchestrator deployment