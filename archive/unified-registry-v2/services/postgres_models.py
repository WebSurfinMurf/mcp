"""
Pydantic models for PostgreSQL MCP service
Provides validation and type safety for all database operations
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from enum import Enum


class SqlOperation(str, Enum):
    """Allowed SQL operations"""
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    
    
class DatabaseFormat(str, Enum):
    """Output format for query results"""
    JSON = "json"
    TABLE = "table"
    CSV = "csv"


class ExecuteSqlParams(BaseModel):
    """Parameters for executing SQL queries"""
    query: str = Field(..., min_length=1, max_length=50000, description="SQL query to execute")
    database: Optional[str] = Field(None, pattern="^[a-zA-Z0-9_]+$", description="Database name")
    timeout: Optional[int] = Field(30, ge=1, le=300, description="Query timeout in seconds")
    format: Optional[DatabaseFormat] = Field(DatabaseFormat.JSON, description="Output format")
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate SQL query for forbidden operations"""
        # Check for forbidden operations in read-only mode
        forbidden_ddl = ['DROP', 'TRUNCATE', 'ALTER', 'GRANT', 'REVOKE', 'CREATE USER', 'CREATE ROLE']
        query_upper = v.upper().strip()
        
        # Check if it's a forbidden DDL operation
        for op in forbidden_ddl:
            if query_upper.startswith(op) or f' {op} ' in query_upper:
                raise ValueError(f"Operation {op} is not allowed")
        
        # Basic SQL injection prevention
        if '--' in v and not v.strip().startswith('--'):
            # Allow comments at the beginning but not inline
            raise ValueError("Inline SQL comments are not allowed")
        
        # Check for multiple statements (unless explicitly allowed)
        if ';' in v:
            statements = [s.strip() for s in v.split(';') if s.strip()]
            if len(statements) > 1:
                # Check if all are SELECT statements
                non_select = [s for s in statements if not s.upper().startswith('SELECT')]
                if non_select:
                    raise ValueError("Multiple statements are only allowed if all are SELECT")
        
        return v


class ListDatabasesParams(BaseModel):
    """Parameters for listing databases"""
    include_system: bool = Field(False, description="Include system databases (postgres, template0, template1)")
    pattern: Optional[str] = Field(None, pattern="^[a-zA-Z0-9_%]+$", description="LIKE pattern for filtering")
    include_size: bool = Field(True, description="Include database sizes")


class ListTablesParams(BaseModel):
    """Parameters for listing tables"""
    database: Optional[str] = Field(None, pattern="^[a-zA-Z0-9_]+$", description="Database name")
    schema_name: str = Field("public", pattern="^[a-zA-Z0-9_]+$", description="Schema name")
    pattern: Optional[str] = Field(None, pattern="^[a-zA-Z0-9_%]+$", description="LIKE pattern for filtering")
    include_system: bool = Field(False, description="Include system tables")
    include_sizes: bool = Field(False, description="Include table sizes (slower)")


class TableInfoParams(BaseModel):
    """Parameters for getting table information"""
    database: Optional[str] = Field(None, pattern="^[a-zA-Z0-9_]+$", description="Database name")
    schema_name: str = Field("public", pattern="^[a-zA-Z0-9_]+$", description="Schema name")
    table: str = Field(..., pattern="^[a-zA-Z0-9_]+$", description="Table name")
    include_indexes: bool = Field(True, description="Include index information")
    include_constraints: bool = Field(True, description="Include constraint information")
    include_stats: bool = Field(False, description="Include table statistics")


class CreateBackupParams(BaseModel):
    """Parameters for creating a database backup"""
    database: str = Field(..., pattern="^[a-zA-Z0-9_]+$", description="Database to backup")
    format: str = Field("custom", pattern="^(plain|custom|tar)$", description="Backup format")
    output_path: Optional[str] = Field(None, description="Output file path")
    schema_only: bool = Field(False, description="Backup schema only (no data)")
    data_only: bool = Field(False, description="Backup data only (no schema)")
    tables: Optional[List[str]] = Field(None, description="Specific tables to backup")
    
    @field_validator('output_path')
    @classmethod
    def validate_output_path(cls, v: Optional[str]) -> Optional[str]:
        """Validate output path is in allowed location"""
        if v:
            # Ensure path is in a safe location
            if not (v.startswith('/tmp/') or v.startswith('/home/administrator/backups/')):
                raise ValueError("Backup path must be in /tmp/ or /home/administrator/backups/")
        return v


class ConnectionPoolParams(BaseModel):
    """Parameters for connection pool configuration"""
    min_connections: int = Field(1, ge=1, le=10, description="Minimum connections in pool")
    max_connections: int = Field(10, ge=1, le=100, description="Maximum connections in pool")
    connection_timeout: int = Field(5, ge=1, le=30, description="Connection timeout in seconds")
    idle_timeout: int = Field(300, ge=60, le=3600, description="Idle connection timeout in seconds")
    recycle_time: int = Field(3600, ge=300, le=7200, description="Connection recycle time in seconds")


class QueryStatsParams(BaseModel):
    """Parameters for getting query statistics"""
    database: Optional[str] = Field(None, pattern="^[a-zA-Z0-9_]+$", description="Database name")
    min_calls: int = Field(10, ge=1, description="Minimum number of calls")
    order_by: str = Field("total_time", pattern="^(calls|total_time|mean_time|max_time)$", description="Sort order")
    limit: int = Field(20, ge=1, le=100, description="Number of results to return")