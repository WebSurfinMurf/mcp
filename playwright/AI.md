# Playwright MCP Service Notes

## Service Overview
**Purpose**: Browser automation and web testing capabilities
**Type**: Custom FastAPI MCP server with Playwright integration
**Port**: 9075
**Network**: Standalone (internet access for web browsing)

## Core Capabilities
- **Web Navigation**: Visit any URL with full JavaScript support
- **Screenshot Capture**: High-quality page screenshots saved to `/tmp`
- **Element Interaction**: Click, fill forms, wait for elements
- **Content Extraction**: Get page text and HTML content
- **Browser Automation**: Full headless Chromium browser control

## Available Tools
1. **`navigate_to(url)`** - Navigate to web pages
2. **`take_screenshot(filename)`** - Capture page screenshots
3. **`click_element(selector)`** - Click page elements by CSS selector
4. **`fill_form_field(selector, value)`** - Fill form inputs
5. **`get_page_content()`** - Extract visible page text
6. **`wait_for_element(selector, timeout)`** - Wait for elements to load

## Technical Implementation
- **Base Image**: mcr.microsoft.com/playwright/python
- **Browser**: Chromium headless mode
- **Framework**: FastAPI with Playwright async integration
- **Volume Mounts**: `/tmp` for screenshot storage
- **Dependencies**: Full Playwright browser binaries included

## Browser Configuration
- **Headless Mode**: True (no GUI)
- **Viewport**: 1280x720 default
- **User Agent**: Standard Chromium user agent
- **JavaScript**: Enabled by default
- **Images**: Loaded for complete page rendering

## Client Registration
**Codex CLI**: `codex mcp add playwright python3 /home/administrator/projects/mcp/playwright/mcp-bridge.py`
**Claude Code**: `claude mcp add playwright http://127.0.0.1:9075/sse --transport sse --scope user`

## Common Use Cases
- Website testing and validation
- Automated screenshot collection
- Form submission testing
- Web scraping with JavaScript support
- UI interaction testing

## File Output
- **Screenshots**: Saved to `/tmp/` directory
- **Filename Format**: User-specified or auto-generated
- **Access**: Files accessible on host at `/tmp/`
- **Format**: PNG images by default

## Troubleshooting
- **Navigation Timeout**: Increase timeout for slow sites
- **Element Not Found**: Verify CSS selectors are correct
- **Screenshot Empty**: Check if page loaded completely
- **Memory Issues**: Browser processes may need restart

## Security Considerations
- **Internet Access**: Container can reach external websites
- **File System**: Limited to `/tmp` directory writes
- **Browser Isolation**: Each session uses isolated browser context
- **No Persistent Storage**: Browser data cleared between sessions

## Integration Points
- **Screenshot Storage**: `/tmp` volume mount
- **Bridge Script**: `/home/administrator/projects/mcp/playwright/mcp-bridge.py`
- **Health Endpoint**: `http://127.0.0.1:9075/health`
- **Browser Binary**: Included in container image