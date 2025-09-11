"""
Monitoring Service Models - Pydantic schemas with MCP 2025-06-18 output schemas
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


# Input Models
class GetContainerLogsInput(BaseModel):
    """Input schema for getting container logs"""
    container_name: str = Field(..., description="Name of the container to get logs from")
    lines: int = Field(50, description="Number of log lines to retrieve", ge=1, le=1000)
    follow: bool = Field(False, description="Whether to follow log output")


class SearchLogsInput(BaseModel):
    """Input schema for searching logs"""
    container_name: str = Field(..., description="Name of the container to search logs")
    query: str = Field(..., description="Search pattern or keyword")
    lines: int = Field(100, description="Number of recent lines to search", ge=1, le=1000)
    case_sensitive: bool = Field(False, description="Whether to use case-sensitive search")


class GetRecentErrorsInput(BaseModel):
    """Input schema for getting recent errors"""
    container_name: Optional[str] = Field(None, description="Container name (if None, searches all)")
    hours: int = Field(24, description="Number of hours to look back", ge=1, le=168)
    error_types: Optional[List[str]] = Field(None, description="Specific error types to filter")


class GetSystemMetricsInput(BaseModel):
    """Input schema for getting system metrics"""
    include_containers: bool = Field(True, description="Include container-specific metrics")
    include_docker: bool = Field(True, description="Include Docker system metrics")


class CheckServiceHealthInput(BaseModel):
    """Input schema for checking service health"""
    service_name: str = Field(..., description="Name of the service to check")
    timeout: int = Field(30, description="Timeout in seconds for health check", ge=1, le=120)


# Output Models (MCP 2025-06-18)
class LogEntry(BaseModel):
    """Individual log entry structure"""
    timestamp: str
    level: Optional[str] = None
    message: str
    container: str
    source: str


class ContainerInfo(BaseModel):
    """Container information structure"""
    name: str
    id: str
    status: str
    image: str
    created: str
    ports: List[str]
    networks: List[str]


class SystemMetrics(BaseModel):
    """System metrics structure"""
    cpu_percent: float
    memory_percent: float
    disk_usage: Dict[str, Any]
    network_io: Dict[str, Any]
    container_count: int
    timestamp: str


class ContainerLogsOutput(BaseModel):
    """Output schema for container logs"""
    container_name: str
    log_entries: List[LogEntry]
    total_lines: int
    truncated: bool
    timestamp: str


class LogSearchOutput(BaseModel):
    """Output schema for log search results"""
    container_name: str
    query: str
    matches: List[LogEntry]
    total_matches: int
    search_lines: int
    case_sensitive: bool
    timestamp: str


class RecentErrorsOutput(BaseModel):
    """Output schema for recent errors"""
    containers_searched: List[str]
    errors: List[LogEntry]
    total_errors: int
    hours_searched: int
    timestamp: str


class SystemMetricsOutput(BaseModel):
    """Output schema for system metrics"""
    system: SystemMetrics
    containers: Optional[List[Dict[str, Any]]] = None
    docker_info: Optional[Dict[str, Any]] = None
    timestamp: str


class ServiceHealthOutput(BaseModel):
    """Output schema for service health checks"""
    service_name: str
    healthy: bool
    status_code: Optional[int] = None
    response_time_ms: float
    error_message: Optional[str] = None
    checked_endpoints: List[str]
    timestamp: str


class HealthOutput(BaseModel):
    """Health check output schema"""
    status: str
    service: str
    version: str
    uptime: float
    tools_count: int
    docker_available: bool
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