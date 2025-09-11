#!/usr/bin/env python3
"""
Monitoring MCP SSE Service - System monitoring and log analysis with Docker integration
Implements MCP 2025-06-18 specification with output schemas and enhanced security
"""

import os
import sys
import asyncio
import json
import re
import time
import psutil
import docker
from datetime import datetime, timedelta
from typing import List, Optional, Any, Dict

# Add core to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core.mcp_sse import MCPSSEServer
from models import (
    GetContainerLogsInput, SearchLogsInput, GetRecentErrorsInput, 
    GetSystemMetricsInput, CheckServiceHealthInput,
    ContainerLogsOutput, LogSearchOutput, RecentErrorsOutput,
    SystemMetricsOutput, ServiceHealthOutput, LogEntry, ContainerInfo,
    SystemMetrics, HealthOutput, ToolListOutput, ErrorOutput
)


class MonitoringService:
    """System monitoring and log analysis service with Docker integration"""
    
    def __init__(self):
        self.docker_client = None
        self.docker_available = False
        self._initialize_docker()
        
    def _initialize_docker(self):
        """Initialize Docker client if available"""
        try:
            self.docker_client = docker.from_env()
            # Test connection
            self.docker_client.ping()
            self.docker_available = True
        except Exception as e:
            print(f"Docker not available: {e}")
            self.docker_available = False

    def _parse_log_line(self, line: str, container_name: str) -> LogEntry:
        """Parse a log line into structured format"""
        # Try to extract timestamp and level from common log formats
        timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})', line)
        level_match = re.search(r'\b(DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\b', line, re.IGNORECASE)
        
        timestamp = timestamp_match.group(1) if timestamp_match else datetime.now().isoformat()
        level = level_match.group(1).upper() if level_match else None
        
        return LogEntry(
            timestamp=timestamp,
            level=level,
            message=line.strip(),
            container=container_name,
            source="docker"
        )

    async def get_container_logs(self, input_data: GetContainerLogsInput) -> ContainerLogsOutput:
        """Get logs from a specific container"""
        if not self.docker_available:
            raise ValueError("Docker is not available")
        
        try:
            container = self.docker_client.containers.get(input_data.container_name)
        except docker.errors.NotFound:
            raise ValueError(f"Container '{input_data.container_name}' not found")
        
        try:
            # Get logs
            logs = container.logs(
                tail=input_data.lines,
                timestamps=True,
                follow=False
            ).decode('utf-8', errors='ignore')
            
            # Parse log lines
            log_lines = logs.strip().split('\n') if logs.strip() else []
            log_entries = []
            
            for line in log_lines:
                if line.strip():
                    log_entries.append(self._parse_log_line(line, input_data.container_name))
            
            # Determine if logs were truncated
            all_logs = container.logs().decode('utf-8', errors='ignore')
            total_lines = len(all_logs.strip().split('\n')) if all_logs.strip() else 0
            truncated = len(log_entries) < total_lines
            
            return ContainerLogsOutput(
                container_name=input_data.container_name,
                log_entries=log_entries,
                total_lines=total_lines,
                truncated=truncated,
                timestamp=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            raise ValueError(f"Failed to get container logs: {e}")

    async def search_logs(self, input_data: SearchLogsInput) -> LogSearchOutput:
        """Search for patterns in container logs"""
        if not self.docker_available:
            raise ValueError("Docker is not available")
        
        try:
            container = self.docker_client.containers.get(input_data.container_name)
        except docker.errors.NotFound:
            raise ValueError(f"Container '{input_data.container_name}' not found")
        
        try:
            # Get recent logs
            logs = container.logs(
                tail=input_data.lines,
                timestamps=True,
                follow=False
            ).decode('utf-8', errors='ignore')
            
            # Search for query in logs
            log_lines = logs.strip().split('\n') if logs.strip() else []
            matches = []
            
            search_flags = 0 if input_data.case_sensitive else re.IGNORECASE
            pattern = re.compile(re.escape(input_data.query), search_flags)
            
            for line in log_lines:
                if line.strip() and pattern.search(line):
                    matches.append(self._parse_log_line(line, input_data.container_name))
            
            return LogSearchOutput(
                container_name=input_data.container_name,
                query=input_data.query,
                matches=matches,
                total_matches=len(matches),
                search_lines=len(log_lines),
                case_sensitive=input_data.case_sensitive,
                timestamp=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            raise ValueError(f"Failed to search logs: {e}")

    async def get_recent_errors(self, input_data: GetRecentErrorsInput) -> RecentErrorsOutput:
        """Get recent error messages from containers"""
        if not self.docker_available:
            raise ValueError("Docker is not available")
        
        errors = []
        containers_searched = []
        
        # Determine which containers to search
        if input_data.container_name:
            try:
                container = self.docker_client.containers.get(input_data.container_name)
                containers_to_search = [container]
            except docker.errors.NotFound:
                raise ValueError(f"Container '{input_data.container_name}' not found")
        else:
            containers_to_search = self.docker_client.containers.list()
        
        # Calculate time threshold
        since_time = datetime.now() - timedelta(hours=input_data.hours)
        
        for container in containers_to_search:
            containers_searched.append(container.name)
            
            try:
                # Get logs since the time threshold
                logs = container.logs(
                    since=since_time,
                    timestamps=True,
                    follow=False
                ).decode('utf-8', errors='ignore')
                
                log_lines = logs.strip().split('\n') if logs.strip() else []
                
                # Look for error patterns
                error_patterns = [
                    r'\b(ERROR|FATAL|CRITICAL)\b',
                    r'\bexception\b',
                    r'\bfailed\b',
                    r'\berror\b'
                ]
                
                if input_data.error_types:
                    error_patterns = [re.escape(et) for et in input_data.error_types]
                
                for line in log_lines:
                    if line.strip():
                        for pattern in error_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                log_entry = self._parse_log_line(line, container.name)
                                errors.append(log_entry)
                                break
                
            except Exception as e:
                # Log the error but continue with other containers
                print(f"Error getting logs from {container.name}: {e}")
                continue
        
        return RecentErrorsOutput(
            containers_searched=containers_searched,
            errors=errors,
            total_errors=len(errors),
            hours_searched=input_data.hours,
            timestamp=datetime.utcnow().isoformat()
        )

    async def get_system_metrics(self, input_data: GetSystemMetricsInput) -> SystemMetricsOutput:
        """Get system and container metrics"""
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        network = psutil.net_io_counters()
        
        system_metrics = SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            disk_usage={
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": (disk.used / disk.total) * 100
            },
            network_io={
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv
            },
            container_count=0,
            timestamp=datetime.utcnow().isoformat()
        )
        
        containers_info = None
        docker_info = None
        
        if self.docker_available:
            try:
                containers = self.docker_client.containers.list()
                system_metrics.container_count = len(containers)
                
                if input_data.include_containers:
                    containers_info = []
                    for container in containers:
                        stats = container.stats(stream=False)
                        containers_info.append({
                            "name": container.name,
                            "id": container.short_id,
                            "status": container.status,
                            "cpu_percent": self._calculate_cpu_percent(stats),
                            "memory_usage": stats['memory_stats'].get('usage', 0),
                            "memory_limit": stats['memory_stats'].get('limit', 0)
                        })
                
                if input_data.include_docker:
                    docker_info = self.docker_client.info()
                    
            except Exception as e:
                print(f"Error getting Docker metrics: {e}")
        
        return SystemMetricsOutput(
            system=system_metrics,
            containers=containers_info,
            docker_info=docker_info,
            timestamp=datetime.utcnow().isoformat()
        )

    def _calculate_cpu_percent(self, stats: dict) -> float:
        """Calculate CPU percentage from Docker stats"""
        try:
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_cpu_delta = stats['cpu_stats']['system_cpu_usage'] - \
                              stats['precpu_stats']['system_cpu_usage']
            
            if system_cpu_delta > 0 and cpu_delta > 0:
                cpu_percent = (cpu_delta / system_cpu_delta) * \
                             len(stats['cpu_stats']['cpu_usage']['percpu_usage']) * 100.0
                return round(cpu_percent, 2)
        except (KeyError, ZeroDivisionError):
            pass
        return 0.0

    async def check_service_health(self, input_data: CheckServiceHealthInput) -> ServiceHealthOutput:
        """Check health of a service by making HTTP requests"""
        import httpx
        
        service_name = input_data.service_name
        timeout = input_data.timeout
        
        # Define common health endpoints to check
        base_urls = [
            f"http://localhost",
            f"http://{service_name}",
            f"http://mcp-{service_name}"
        ]
        
        # Common service ports (could be made configurable)
        service_ports = {
            "postgres": 8001,
            "fetch": 8002,
            "filesystem": 8003,
            "github": 8004,
            "monitoring": 8005
        }
        
        port = service_ports.get(service_name, 8000)
        endpoints_to_check = ["/health", "/", "/status"]
        
        checked_endpoints = []
        best_result = None
        
        for base_url in base_urls:
            for endpoint in endpoints_to_check:
                url = f"{base_url}:{port}{endpoint}"
                checked_endpoints.append(url)
                
                try:
                    start_time = time.time()
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        response = await client.get(url)
                    
                    response_time = (time.time() - start_time) * 1000
                    
                    if response.status_code == 200:
                        return ServiceHealthOutput(
                            service_name=service_name,
                            healthy=True,
                            status_code=response.status_code,
                            response_time_ms=round(response_time, 2),
                            error_message=None,
                            checked_endpoints=checked_endpoints,
                            timestamp=datetime.utcnow().isoformat()
                        )
                    else:
                        best_result = {
                            "status_code": response.status_code,
                            "response_time": response_time,
                            "error": f"HTTP {response.status_code}"
                        }
                        
                except Exception as e:
                    if best_result is None:
                        best_result = {
                            "status_code": None,
                            "response_time": 0,
                            "error": str(e)
                        }
                    continue
        
        # If we get here, no endpoint was successful
        return ServiceHealthOutput(
            service_name=service_name,
            healthy=False,
            status_code=best_result.get("status_code") if best_result else None,
            response_time_ms=best_result.get("response_time", 0) if best_result else 0,
            error_message=best_result.get("error", "Service unreachable") if best_result else "Service unreachable",
            checked_endpoints=checked_endpoints,
            timestamp=datetime.utcnow().isoformat()
        )


async def create_mcp_server() -> MCPSSEServer:
    """Create and configure the monitoring MCP SSE server"""
    
    # Initialize service
    monitoring_service = MonitoringService()
    
    # Create server with service info
    server = MCPSSEServer(
        name="monitoring",
        version="1.0.0",
        port=int(os.getenv('SERVICE_PORT', 8005))
    )
    
    # Register tools with input/output schemas
    server.register_tool(
        name="get_container_logs",
        handler=monitoring_service.get_container_logs,
        input_schema=GetContainerLogsInput,
        output_schema=ContainerLogsOutput,
        description="Get logs from a specific Docker container"
    )
    
    server.register_tool(
        name="search_logs",
        handler=monitoring_service.search_logs,
        input_schema=SearchLogsInput,
        output_schema=LogSearchOutput,
        description="Search for patterns in container logs"
    )
    
    server.register_tool(
        name="get_recent_errors",
        handler=monitoring_service.get_recent_errors,
        input_schema=GetRecentErrorsInput,
        output_schema=RecentErrorsOutput,
        description="Get recent error messages from containers"
    )
    
    server.register_tool(
        name="get_system_metrics",
        handler=monitoring_service.get_system_metrics,
        input_schema=GetSystemMetricsInput,
        output_schema=SystemMetricsOutput,
        description="Get system and container performance metrics"
    )
    
    server.register_tool(
        name="check_service_health",
        handler=monitoring_service.check_service_health,
        input_schema=CheckServiceHealthInput,
        output_schema=ServiceHealthOutput,
        description="Check health status of a service by making HTTP requests"
    )
    
    return server


async def main():
    """Main entry point"""
    try:
        server = await create_mcp_server()
        await server.run_async()
    except Exception as e:
        print(f"Failed to start monitoring service: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())