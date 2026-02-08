# MCP Gemini Image Server

Google Gemini (Nano Banana Pro) image generation via MCP protocol.

**Owner**: administrator@linuxserver.lan

---

## Overview

AI image generation using Google's Gemini models. Generates images from text prompts.

**Use Cases:**
- Generate specific images stock photos can't provide
- Create culturally-accurate imagery (e.g., "Irish flat cap on tweed")
- Custom images with accurate text rendering

---

## Implementation

**CURRENT**: Using `mcp-image` npm package by shinpr
- NPM: `npx -y mcp-image`
- Integrated via MCP Proxy (stdio transport)
- No separate container needed

**DEPRECATED**: Custom FastAPI server in `src/server.py`
- Docker container on port 48014
- Replaced with npm package for simplicity

---

## Tools (1)

| Tool | Description |
|------|-------------|
| `generate_image` | Generate image from text prompt using Gemini |

---

## Configuration

**API Key Location:** `/home/administrator/projects/secrets/gemini-image.env`
```bash
GEMINI_API_KEY=your_api_key_here
```

**Proxy Config:** `/home/administrator/projects/mcp/proxy/config.json`
```json
"gemini-image": {
  "command": "npx",
  "args": ["-y", "mcp-image"],
  "env": {
    "NODE_NO_WARNINGS": "1",
    "GEMINI_API_KEY": "...",
    "IMAGE_OUTPUT_DIR": "/generated-images"
  }
}
```

**Output Directory:** `/home/administrator/projects/nginx/sites/generated-images/`
- Images saved here are web-accessible
- URL: `https://nginx.ai-servicers.com/generated-images/`

---

## Usage Example

```bash
curl -s -X POST http://localhost:9090/gemini-image/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "generate_image",
      "arguments": {
        "prompt": "Traditional Irish flat cap made of grey Donegal tweed"
      }
    },
    "id": 1
  }'
```

---

## Model

| Model | Internal Name | Description |
|-------|---------------|-------------|
| Default | gemini-3-pro-image-preview | High quality image generation |

---

## Network

| Network | Purpose |
|---------|---------|
| mcp-net | MCP proxy access |

---

## Architecture

```
MCP Proxy (9090)
    ↓ npx stdio
mcp-image (npm package)
    ↓ REST API
Google Gemini API
    ↓
Generated images → /nginx/sites/generated-images/
```

---

*Last Updated: 2025-12-07*
