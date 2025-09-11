#!/usr/bin/env python3
"""
Filesystem MCP SSE Service - Secure file operations with path restrictions
Implements MCP 2025-06-18 specification with output schemas and enhanced security
"""

import os
import sys
import asyncio
import json
import stat
import aiofiles
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Any, Dict

# Add core to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core.mcp_sse import MCPSSEServer
from models import (
    ReadFileInput, WriteFileInput, ListDirectoryInput, DeleteFileInput,
    FileContentOutput, FileWriteOutput, DirectoryListOutput, FileDeleteOutput,
    FileInfo, HealthOutput, ToolListOutput, ErrorOutput
)


class FilesystemService:
    """Secure filesystem operations with path restrictions"""
    
    def __init__(self):
        self.allowed_paths = self._get_allowed_paths()
        self.max_file_size = 10 * 1024 * 1024  # 10MB limit
        self.max_lines = 10000  # Maximum lines to read
        
    def _get_allowed_paths(self) -> List[str]:
        """Get allowed filesystem paths from environment"""
        allowed = os.getenv('ALLOWED_PATHS', '/workspace,/shared')
        paths = [path.strip() for path in allowed.split(',')]
        # Ensure all paths are absolute and exist
        result = []
        for path in paths:
            if os.path.isabs(path) and os.path.exists(path):
                result.append(os.path.realpath(path))
        return result
    
    def _is_path_allowed(self, file_path: str) -> bool:
        """Check if a file path is within allowed directories"""
        try:
            real_path = os.path.realpath(file_path)
            for allowed in self.allowed_paths:
                if real_path.startswith(allowed + os.sep) or real_path == allowed:
                    return True
            return False
        except (OSError, ValueError):
            return False
    
    def _get_file_info(self, file_path: str) -> FileInfo:
        """Get detailed file information"""
        try:
            stat_info = os.stat(file_path)
            file_type = "directory" if stat.S_ISDIR(stat_info.st_mode) else "file"
            
            # Format permissions
            mode = stat_info.st_mode
            perms = stat.filemode(mode)
            
            # Check read/write permissions
            is_readable = os.access(file_path, os.R_OK)
            is_writable = os.access(file_path, os.W_OK)
            
            return FileInfo(
                name=os.path.basename(file_path),
                path=file_path,
                size=stat_info.st_size,
                type=file_type,
                modified=datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                permissions=perms,
                is_readable=is_readable,
                is_writable=is_writable
            )
        except OSError as e:
            raise ValueError(f"Cannot access file info: {e}")

    async def read_file(self, input_data: ReadFileInput) -> FileContentOutput:
        """Read file contents with optional line limits"""
        if not self._is_path_allowed(input_data.file_path):
            raise ValueError(f"Access denied: Path not in allowed directories")
        
        if not os.path.exists(input_data.file_path):
            raise ValueError(f"File does not exist: {input_data.file_path}")
        
        if not os.path.isfile(input_data.file_path):
            raise ValueError(f"Path is not a file: {input_data.file_path}")
        
        # Check file size
        file_size = os.path.getsize(input_data.file_path)
        if file_size > self.max_file_size:
            raise ValueError(f"File too large: {file_size} bytes (max {self.max_file_size})")
        
        try:
            async with aiofiles.open(input_data.file_path, 'r', encoding='utf-8') as f:
                all_lines = await f.readlines()
            
            total_lines = len(all_lines)
            start_line = (input_data.offset or 1) - 1
            max_lines = input_data.line_limit or self.max_lines
            
            # Apply offset and limit
            selected_lines = all_lines[start_line:start_line + max_lines]
            content = ''.join(selected_lines)
            
            # Check if content was truncated
            truncated = len(selected_lines) < (total_lines - start_line)
            
            return FileContentOutput(
                file_path=input_data.file_path,
                content=content,
                lines_read=len(selected_lines),
                total_lines=total_lines,
                encoding='utf-8',
                truncated=truncated
            )
            
        except UnicodeDecodeError:
            raise ValueError(f"File is not valid UTF-8: {input_data.file_path}")
        except OSError as e:
            raise ValueError(f"Cannot read file: {e}")

    async def write_file(self, input_data: WriteFileInput) -> FileWriteOutput:
        """Write content to file with optional append mode"""
        if not self._is_path_allowed(input_data.file_path):
            raise ValueError(f"Access denied: Path not in allowed directories")
        
        # Check if file exists
        file_existed = os.path.exists(input_data.file_path)
        
        # Ensure parent directory exists
        parent_dir = os.path.dirname(input_data.file_path)
        if not os.path.exists(parent_dir):
            if not self._is_path_allowed(parent_dir):
                raise ValueError(f"Access denied: Cannot create parent directory")
            os.makedirs(parent_dir, exist_ok=True)
        
        try:
            mode = 'a' if input_data.append else 'w'
            async with aiofiles.open(input_data.file_path, mode, encoding='utf-8') as f:
                await f.write(input_data.content)
            
            # Get file size for bytes written
            file_size = os.path.getsize(input_data.file_path)
            bytes_written = len(input_data.content.encode('utf-8'))
            
            return FileWriteOutput(
                file_path=input_data.file_path,
                bytes_written=bytes_written,
                success=True,
                created=not file_existed
            )
            
        except OSError as e:
            raise ValueError(f"Cannot write file: {e}")

    async def list_directory(self, input_data: ListDirectoryInput) -> DirectoryListOutput:
        """List directory contents with optional recursion"""
        if not self._is_path_allowed(input_data.directory_path):
            raise ValueError(f"Access denied: Path not in allowed directories")
        
        if not os.path.exists(input_data.directory_path):
            raise ValueError(f"Directory does not exist: {input_data.directory_path}")
        
        if not os.path.isdir(input_data.directory_path):
            raise ValueError(f"Path is not a directory: {input_data.directory_path}")
        
        files = []
        total_files = 0
        total_directories = 0
        access_error = None
        
        try:
            if input_data.recursive:
                # Recursive listing
                for root, dirs, filenames in os.walk(input_data.directory_path):
                    # Filter hidden files if not requested
                    if not input_data.include_hidden:
                        dirs[:] = [d for d in dirs if not d.startswith('.')]
                        filenames = [f for f in filenames if not f.startswith('.')]
                    
                    # Add directories
                    for dirname in dirs:
                        dir_path = os.path.join(root, dirname)
                        try:
                            files.append(self._get_file_info(dir_path))
                            total_directories += 1
                        except ValueError:
                            continue
                    
                    # Add files
                    for filename in filenames:
                        file_path = os.path.join(root, filename)
                        try:
                            files.append(self._get_file_info(file_path))
                            total_files += 1
                        except ValueError:
                            continue
            else:
                # Non-recursive listing
                for item in os.listdir(input_data.directory_path):
                    if not input_data.include_hidden and item.startswith('.'):
                        continue
                    
                    item_path = os.path.join(input_data.directory_path, item)
                    try:
                        file_info = self._get_file_info(item_path)
                        files.append(file_info)
                        if file_info.type == 'directory':
                            total_directories += 1
                        else:
                            total_files += 1
                    except ValueError:
                        continue
            
        except OSError as e:
            access_error = f"Access error: {e}"
        
        return DirectoryListOutput(
            directory_path=input_data.directory_path,
            files=sorted(files, key=lambda x: (x.type != 'directory', x.name.lower())),
            total_files=total_files,
            total_directories=total_directories,
            access_error=access_error
        )

    async def delete_file(self, input_data: DeleteFileInput) -> FileDeleteOutput:
        """Delete a file with confirmation requirement"""
        if not input_data.confirm:
            raise ValueError("Deletion requires confirmation flag to be True")
        
        if not self._is_path_allowed(input_data.file_path):
            raise ValueError(f"Access denied: Path not in allowed directories")
        
        file_existed = os.path.exists(input_data.file_path)
        
        if not file_existed:
            return FileDeleteOutput(
                file_path=input_data.file_path,
                success=True,
                existed=False
            )
        
        if os.path.isdir(input_data.file_path):
            raise ValueError(f"Cannot delete directory (use appropriate directory deletion tool)")
        
        try:
            os.remove(input_data.file_path)
            return FileDeleteOutput(
                file_path=input_data.file_path,
                success=True,
                existed=True
            )
        except OSError as e:
            raise ValueError(f"Cannot delete file: {e}")


async def create_mcp_server() -> MCPSSEServer:
    """Create and configure the filesystem MCP SSE server"""
    
    # Initialize service
    filesystem_service = FilesystemService()
    
    # Create server with service info
    server = MCPSSEServer(
        name="filesystem",
        version="1.0.0",
        port=int(os.getenv('SERVICE_PORT', 8003))
    )
    
    # Register tools with input/output schemas
    server.register_tool(
        name="read_file",
        handler=filesystem_service.read_file,
        input_schema=ReadFileInput,
        output_schema=FileContentOutput,
        description="Read file contents with optional line limits and offset"
    )
    
    server.register_tool(
        name="write_file", 
        handler=filesystem_service.write_file,
        input_schema=WriteFileInput,
        output_schema=FileWriteOutput,
        description="Write content to file with optional append mode"
    )
    
    server.register_tool(
        name="list_directory",
        handler=filesystem_service.list_directory,
        input_schema=ListDirectoryInput,
        output_schema=DirectoryListOutput,
        description="List directory contents with optional recursion and hidden files"
    )
    
    server.register_tool(
        name="delete_file",
        handler=filesystem_service.delete_file,
        input_schema=DeleteFileInput,
        output_schema=FileDeleteOutput,
        description="Delete a file with confirmation requirement"
    )
    
    
    return server


async def main():
    """Main entry point"""
    try:
        server = await create_mcp_server()
        await server.run_async()
    except Exception as e:
        print(f"Failed to start filesystem service: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())