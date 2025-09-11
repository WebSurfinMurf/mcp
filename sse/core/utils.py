"""
Utility functions for MCP SSE services
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime


def setup_logging(service_name: str, level: str = "INFO") -> logging.Logger:
    """Set up structured logging for a service"""
    logger = logging.getLogger(service_name)
    
    # Create handler if not exists
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "service": "%(name)s", '
            '"level": "%(levelname)s", "message": "%(message)s"}'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, level.upper()))
    
    return logger


def load_environment_variables(required_vars: list = None) -> Dict[str, str]:
    """Load and validate environment variables"""
    env_vars = {}
    missing_vars = []
    
    if required_vars:
        for var in required_vars:
            value = os.getenv(var)
            if value:
                env_vars[var] = value
            else:
                missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {missing_vars}")
    
    return env_vars


def validate_tool_schema(schema: dict) -> bool:
    """Validate that a tool schema is valid JSON Schema"""
    required_keys = ["type", "properties"]
    
    if not isinstance(schema, dict):
        return False
    
    if schema.get("type") != "object":
        return False
    
    if "properties" not in schema:
        return False
    
    return True


def create_sse_event(event_type: str, data: Dict[str, Any], event_id: Optional[str] = None) -> str:
    """Create a Server-Sent Event formatted string"""
    lines = []
    
    if event_id:
        lines.append(f"id: {event_id}")
    
    lines.append(f"event: {event_type}")
    lines.append(f"data: {json.dumps(data)}")
    lines.append("")  # Empty line terminates the event
    
    return "\n".join(lines) + "\n"


def parse_connection_string(connection_string: str) -> Dict[str, str]:
    """Parse a database connection string into components"""
    # Simple parser for postgresql:// URLs
    if not connection_string.startswith("postgresql://"):
        raise ValueError("Only PostgreSQL connection strings supported")
    
    # Remove protocol
    connection_string = connection_string[13:]  # Remove "postgresql://"
    
    # Split user:pass@host:port/database
    if "@" in connection_string:
        auth_part, host_part = connection_string.split("@", 1)
        if ":" in auth_part:
            user, password = auth_part.split(":", 1)
        else:
            user = auth_part
            password = ""
    else:
        user = password = ""
        host_part = connection_string
    
    if "/" in host_part:
        host_port, database = host_part.split("/", 1)
    else:
        host_port = host_part
        database = ""
    
    if ":" in host_port:
        host, port = host_port.split(":", 1)
        port = int(port)
    else:
        host = host_port
        port = 5432
    
    return {
        "user": user,
        "password": password,
        "host": host,
        "port": str(port),
        "database": database
    }


async def wait_for_signal():
    """Wait for shutdown signals"""
    import signal
    
    def signal_handler(signum, frame):
        raise KeyboardInterrupt()
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def safe_json_loads(text: str) -> Optional[Dict[str, Any]]:
    """Safely load JSON, returning None on error"""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def get_service_uptime(start_time: datetime) -> float:
    """Calculate service uptime in seconds"""
    return (datetime.now() - start_time).total_seconds()