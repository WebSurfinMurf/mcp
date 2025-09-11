"""
Pydantic models for PostgreSQL MCP SSE service
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class ListDatabasesInput(BaseModel):
    """Input for list_databases tool"""
    include_size: bool = Field(
        default=False, 
        description="Include database size information"
    )


class ExecuteSqlInput(BaseModel):
    """Input for execute_sql tool"""
    query: str = Field(
        ..., 
        description="SQL query to execute",
        max_length=10000
    )
    database: str = Field(
        default="postgres", 
        description="Database name to connect to"
    )
    limit: int = Field(
        default=100,
        description="Maximum number of rows to return",
        ge=1,
        le=1000
    )


class ListTablesInput(BaseModel):
    """Input for list_tables tool"""
    database: str = Field(
        default="postgres", 
        description="Database name to list tables from"
    )
    schema: str = Field(
        default="public",
        description="Schema name to list tables from"
    )


class TableInfoInput(BaseModel):
    """Input for table_info tool"""
    table: str = Field(
        ..., 
        description="Table name to get information about"
    )
    database: str = Field(
        default="postgres", 
        description="Database name containing the table"
    )
    schema: str = Field(
        default="public",
        description="Schema name containing the table"
    )


class QueryStatsInput(BaseModel):
    """Input for query_stats tool"""
    database: str = Field(
        default="postgres", 
        description="Database to get statistics for"
    )
    limit: int = Field(
        default=10,
        description="Number of top queries to return",
        ge=1,
        le=50
    )


# Response models for structured output
class DatabaseInfo(BaseModel):
    """Database information"""
    name: str
    owner: str
    encoding: str
    collation: str
    size_bytes: Optional[int] = None
    size_pretty: Optional[str] = None


class TableInfo(BaseModel):
    """Table information"""
    table_name: str
    schema_name: str
    table_type: str
    row_count: Optional[int] = None
    size_bytes: Optional[int] = None
    size_pretty: Optional[str] = None


class ColumnInfo(BaseModel):
    """Column information"""
    column_name: str
    data_type: str
    is_nullable: bool
    column_default: Optional[str] = None
    is_primary_key: bool = False
    is_foreign_key: bool = False


class QueryResult(BaseModel):
    """Query execution result"""
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    execution_time_ms: float


# Output schemas for MCP 2025-06-18
class DatabaseListOutput(BaseModel):
    """Output schema for list_databases tool"""
    content: List[Dict[str, Any]] = Field(..., description="MCP content format")


class SQLExecutionOutput(BaseModel):
    """Output schema for execute_sql tool"""
    content: List[Dict[str, Any]] = Field(..., description="MCP content format")
    isError: Optional[bool] = Field(default=False, description="Whether this is an error result")


class TableListOutput(BaseModel):
    """Output schema for list_tables tool"""
    content: List[Dict[str, Any]] = Field(..., description="MCP content format")


class TableInfoOutput(BaseModel):
    """Output schema for table_info tool"""
    content: List[Dict[str, Any]] = Field(..., description="MCP content format")


class QueryStatsOutput(BaseModel):
    """Output schema for query_stats tool"""
    content: List[Dict[str, Any]] = Field(..., description="MCP content format")