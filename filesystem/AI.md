# Filesystem MCP Service Notes

## Service Overview
**Purpose**: Provides secure file system access within the project workspace
**Type**: Custom FastAPI MCP server with dual transport support
**Port**: 9073
**Network**: Standalone (no external dependencies)

## Core Capabilities
- **File Operations**: Read, write, list files with proper permissions
- **Directory Traversal**: Safe navigation within workspace boundaries
- **Path Translation**: Handles both absolute and relative paths correctly
- **Symlink Handling**: Graceful error handling for broken symlinks

## Available Tools
1. **`list_files(path)`** - List directory contents with metadata (size, modified time)
2. **`read_file(path)`** - Read file contents with encoding detection
3. **`write_file(path, content)`** - Write files to `/tmp` directory only
4. **`get_file_info(path)`** - Get detailed file/directory statistics

## Technical Implementation
- **Base Image**: python:3.11-slim
- **Framework**: FastAPI with custom MCP protocol handlers
- **Volume Mounts**: `/home/administrator/projects:/workspace:ro` (read-only)
- **Write Access**: Limited to `/tmp` directory for security
- **Path Handling**: Smart translation between host paths and container paths

## Security Model
- **Read-Only Workspace**: Project files mounted as read-only
- **Restricted Writes**: Only `/tmp` directory writable
- **Path Validation**: Prevents directory traversal attacks
- **Container Isolation**: No network access, isolated file system

## Client Registration
**Codex CLI**: `codex mcp add filesystem python3 /home/administrator/projects/mcp/filesystem/mcp-bridge.py`
**Claude Code**: `claude mcp add filesystem http://127.0.0.1:9073/sse --transport sse --scope user`

## Common Use Cases
- Reading project configuration files
- Analyzing code structure and dependencies
- Temporary file creation for processing
- Safe file exploration without shell access

## Troubleshooting
- **Permission Errors**: Check if trying to write outside `/tmp`
- **Path Not Found**: Verify path exists in `/workspace` mount
- **Symlink Issues**: Broken symlinks return graceful errors
- **Container Issues**: Check `docker ps | grep mcp-filesystem`

## Integration Points
- **Workspace Mount**: `/home/administrator/projects` → `/workspace`
- **Temp Directory**: `/tmp` for write operations
- **Bridge Script**: `/home/administrator/projects/mcp/filesystem/mcp-bridge.py`
- **Health Endpoint**: `http://127.0.0.1:9073/health`