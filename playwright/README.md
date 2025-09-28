# Playwright MCP Service

Browser automation service providing Playwright functionality via the Model Context Protocol (MCP).

## Overview

This service exposes Playwright browser automation capabilities through MCP, allowing AI assistants to interact with web pages programmatically. It runs in a containerized environment with Chromium browser support.

## Features

- **Web Navigation**: Navigate to URLs and retrieve page information
- **Screenshots**: Capture full page or viewport screenshots
- **Text Extraction**: Extract text content from pages or specific elements
- **Element Interaction**: Click buttons, links, and other interactive elements
- **Form Automation**: Fill out web forms automatically
- **Page Analysis**: Get comprehensive page metadata and structure info

## Architecture

- **FastAPI** server providing HTTP and SSE endpoints
- **Playwright** with Chromium browser for automation
- **Docker** containerization with shared memory for browser stability
- **Bridge script** for Codex CLI stdio integration

## Deployment

Deploy using the provided script:
```bash
./deploy.sh
```

This will:
1. Build and start the Docker container
2. Perform health checks
3. Verify MCP protocol functionality
4. Update documentation

## Integration

### Codex CLI
```bash
codex mcp add playwright python3 /path/to/mcp-bridge.py
```

### Claude Code CLI
```bash
claude mcp add playwright http://127.0.0.1:9075/sse --transport sse --scope user
```

## API Endpoints

- `GET /health` - Health check
- `GET /sse` - Server-Sent Events for MCP
- `POST /mcp` - HTTP POST for MCP requests

## Tools

1. **navigate_to_page** - Basic page navigation
2. **take_screenshot** - Capture page screenshots
3. **extract_text** - Extract text content
4. **click_element** - Interact with page elements
5. **fill_form** - Automated form filling
6. **get_page_info** - Comprehensive page analysis

## Configuration

Environment variables (via `/home/administrator/secrets/mcp-playwright.env`):
- `MCP_SERVER_NAME`: Service identifier
- `TEMP_PATH`: Temporary file storage location
- `PLAYWRIGHT_BROWSERS_PATH`: Browser installation path

## Network

- **Port**: 9075 (external) → 8000 (internal)
- **Binding**: 127.0.0.1 (localhost only)
- **Protocol**: HTTP with SSE support

## Security

- No external network access required
- Runs in isolated container environment
- Temporary files stored in mounted `/tmp` volume
- Headless browser mode for security