"""
Filesystem Service Models - Pydantic schemas with MCP 2025-06-18 output schemas
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


# Input Models
class ReadFileInput(BaseModel):
    """Input schema for reading files"""
    file_path: str = Field(..., description="Absolute path to the file to read")
    line_limit: Optional[int] = Field(None, description="Maximum number of lines to read", ge=1)
    offset: Optional[int] = Field(None, description="Line number to start reading from", ge=1)


class WriteFileInput(BaseModel):
    """Input schema for writing files"""
    file_path: str = Field(..., description="Absolute path to the file to write")
    content: str = Field(..., description="Content to write to the file")
    append: bool = Field(False, description="Whether to append to existing file")


class ListDirectoryInput(BaseModel):
    """Input schema for listing directory contents"""
    directory_path: str = Field(..., description="Absolute path to directory to list")
    recursive: bool = Field(False, description="Whether to list recursively")
    include_hidden: bool = Field(False, description="Whether to include hidden files")


class DeleteFileInput(BaseModel):
    """Input schema for deleting files"""
    file_path: str = Field(..., description="Absolute path to the file to delete")
    confirm: bool = Field(False, description="Confirmation flag to prevent accidental deletion")


# Output Models (MCP 2025-06-18)
class FileInfo(BaseModel):
    """File information structure"""
    name: str
    path: str
    size: int
    type: str  # "file" or "directory"
    modified: str
    permissions: str
    is_readable: bool
    is_writable: bool


class FileContentOutput(BaseModel):
    """Output schema for file read operations"""
    file_path: str
    content: str
    lines_read: int
    total_lines: Optional[int] = None
    encoding: str = "utf-8"
    truncated: bool = False


class FileWriteOutput(BaseModel):
    """Output schema for file write operations"""
    file_path: str
    bytes_written: int
    success: bool
    created: bool  # True if file was created, False if modified


class DirectoryListOutput(BaseModel):
    """Output schema for directory listing"""
    directory_path: str
    files: List[FileInfo]
    total_files: int
    total_directories: int
    access_error: Optional[str] = None


class FileDeleteOutput(BaseModel):
    """Output schema for file deletion"""
    file_path: str
    success: bool
    existed: bool  # True if file existed before deletion


class HealthOutput(BaseModel):
    """Health check output schema"""
    status: str
    service: str
    version: str
    uptime: float
    tools_count: int
    allowed_paths: List[str]
    timestamp: str


class ToolListOutput(BaseModel):
    """Tool listing output schema"""
    tools: List[Dict[str, Any]]
    service: str
    version: str


class ErrorOutput(BaseModel):
    """Error response schema"""
    error: str
    details: Optional[str] = None
    error_code: Optional[str] = None