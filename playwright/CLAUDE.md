# Claude Code MCP Integration

This service provides browser automation tools for Claude Code CLI via the Model Context Protocol (MCP).

## Configuration

Add this to your Claude Code MCP configuration:

```bash
claude mcp add playwright http://127.0.0.1:9075/sse --transport sse --scope user
```

## Available Tools

- **navigate_to_page**: Navigate to a web page and get basic information
- **take_screenshot**: Take a screenshot of a web page
- **extract_text**: Extract text content from a web page
- **click_element**: Click an element on a web page
- **fill_form**: Fill out form fields on a web page
- **get_page_info**: Get comprehensive information about a web page

## Service Details

- **Container**: mcp-playwright
- **Port**: 127.0.0.1:9075
- **SSE Endpoint**: http://127.0.0.1:9075/sse
- **Health Check**: http://127.0.0.1:9075/health
- **Browser**: Chromium (headless)
- **Environment**: /home/administrator/secrets/mcp-playwright.env

## Example Usage

Navigate to a page:
```
Navigate to https://example.com
```

Take a screenshot:
```
Take a screenshot of https://example.com and save it as example.png
```

Extract text from a specific element:
```
Extract text from the main heading on https://example.com
```