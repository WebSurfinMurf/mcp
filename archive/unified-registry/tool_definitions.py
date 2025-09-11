"""
Central Tool Registry for Unified MCP System
Defines all MCP tools in one place for both Claude Code and LiteLLM
"""

TOOL_DEFINITIONS = {
    "filesystem": {
        "service": "filesystem",
        "endpoint": "http://localhost:8585/servers/filesystem/sse",
        "docker_command": ["bash", "/home/administrator/projects/mcp/filesystem/mcp-wrapper-admin.sh"],
        "tools": [
            {
                "name": "read_file",
                "mcp_name": "read_file",
                "description": "Read the contents of a file at the specified path",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The path to the file to read"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "list_directory",
                "mcp_name": "list_directory", 
                "description": "List the contents of a directory",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The path to the directory to list"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "write_file",
                "mcp_name": "write_file",
                "description": "Write content to a file at the specified path",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The path to write the file to"
                        },
                        "content": {
                            "type": "string",
                            "description": "The content to write to the file"
                        }
                    },
                    "required": ["path", "content"]
                }
            },
            {
                "name": "create_directory",
                "mcp_name": "create_directory",
                "description": "Create a new directory at the specified path",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The path of the directory to create"
                        }
                    },
                    "required": ["path"]
                }
            }
        ]
    },
    "postgres": {
        "service": "postgres",
        "endpoint": "http://localhost:8585/servers/postgres/sse",
        "docker_command": ["bash", "/home/administrator/projects/mcp/postgres/mcp-wrapper.sh"],
        "tools": [
            {
                "name": "list_databases",
                "mcp_name": "list_databases",
                "description": "List all databases in the PostgreSQL server",
                "parameters_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "execute_sql",
                "mcp_name": "execute_sql",
                "description": "Execute an SQL query on the database",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": "The SQL query to execute"
                        },
                        "database": {
                            "type": "string",
                            "description": "The database to execute the query on (optional)",
                            "default": "postgres"
                        }
                    },
                    "required": ["sql"]
                }
            }
        ]
    },
    "github": {
        "service": "github",
        "endpoint": "http://localhost:8585/servers/github/sse",
        "command": ["npx", "@modelcontextprotocol/server-github"],
        "env": {
            "GITHUB_PERSONAL_ACCESS_TOKEN": "GITHUB_TOKEN_PLACEHOLDER"
        },
        "tools": [
            {
                "name": "search_repositories",
                "mcp_name": "search_repositories", 
                "description": "Search for GitHub repositories",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for repositories"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_repository",
                "mcp_name": "get_repository",
                "description": "Get details about a specific GitHub repository",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner username"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name"
                        }
                    },
                    "required": ["owner", "repo"]
                }
            },
            {
                "name": "create_issue",
                "mcp_name": "create_issue",
                "description": "Create a new issue in a GitHub repository",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner username"
                        },
                        "repo": {
                            "type": "string", 
                            "description": "Repository name"
                        },
                        "title": {
                            "type": "string",
                            "description": "Issue title"
                        },
                        "body": {
                            "type": "string",
                            "description": "Issue body content"
                        }
                    },
                    "required": ["owner", "repo", "title"]
                }
            }
        ]
    },
    "monitoring": {
        "service": "monitoring",
        "endpoint": "http://localhost:8585/servers/monitoring/sse",
        "command": ["node", "/home/administrator/projects/mcp/monitoring/src/index.js"],
        "env": {
            "LOKI_URL": "http://localhost:3100",
            "NETDATA_URL": "http://localhost:19999"
        },
        "tools": [
            {
                "name": "search_logs",
                "mcp_name": "search_logs",
                "description": "Search logs using LogQL query language",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "LogQL query (e.g., {container_name=\"nginx\"} |= \"error\")"
                        },
                        "hours": {
                            "type": "number",
                            "description": "Hours to look back (default: 24)",
                            "default": 24
                        },
                        "limit": {
                            "type": "number",
                            "description": "Maximum results to return (default: 100)",
                            "default": 100
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_recent_errors",
                "mcp_name": "get_recent_errors",
                "description": "Get recent error-level logs from all containers",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "hours": {
                            "type": "number",
                            "description": "Hours to look back (default: 1)",
                            "default": 1
                        },
                        "container": {
                            "type": "string",
                            "description": "Optional: specific container name"
                        }
                    }
                }
            },
            {
                "name": "get_container_logs",
                "mcp_name": "get_container_logs",
                "description": "Get logs for a specific container",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "container_name": {
                            "type": "string",
                            "description": "Name of the container"
                        },
                        "hours": {
                            "type": "number",
                            "description": "Hours to look back (default: 1)",
                            "default": 1
                        },
                        "filter": {
                            "type": "string",
                            "description": "Optional text filter"
                        }
                    },
                    "required": ["container_name"]
                }
            },
            {
                "name": "get_system_metrics",
                "mcp_name": "get_system_metrics",
                "description": "Get current system metrics from Netdata",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "charts": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific charts to retrieve",
                            "default": ["system.cpu", "system.ram", "disk.util"]
                        },
                        "after": {
                            "type": "number",
                            "description": "Seconds to look back (default: 300)",
                            "default": 300
                        }
                    }
                }
            },
            {
                "name": "check_service_health",
                "mcp_name": "check_service_health",
                "description": "Check health of a specific service using logs and metrics",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "service_name": {
                            "type": "string",
                            "description": "Name of the service/container"
                        },
                        "check_errors": {
                            "type": "boolean",
                            "description": "Check for recent errors (default: true)",
                            "default": True
                        },
                        "check_restarts": {
                            "type": "boolean",
                            "description": "Check for recent restarts (default: true)",
                            "default": True
                        }
                    },
                    "required": ["service_name"]
                }
            }
        ]
    },
    "n8n": {
        "service": "n8n",
        "endpoint": "http://localhost:8585/servers/n8n/sse",
        "command": ["bash", "/home/administrator/projects/mcp/n8n/mcp-wrapper.sh"],
        "tools": [
            {
                "name": "list_workflows",
                "mcp_name": "list_workflows",
                "description": "List all n8n workflows",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "active": {
                            "type": "boolean",
                            "description": "Filter by active status"
                        }
                    }
                }
            },
            {
                "name": "get_workflow",
                "mcp_name": "get_workflow",
                "description": "Get details of a specific workflow",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Workflow ID"
                        }
                    },
                    "required": ["id"]
                }
            },
            {
                "name": "execute_workflow",
                "mcp_name": "execute_workflow",
                "description": "Execute a workflow with optional input data",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Workflow ID"
                        },
                        "data": {
                            "type": "object",
                            "description": "Input data for the workflow"
                        }
                    },
                    "required": ["id"]
                }
            }
        ]
    },
    "playwright": {
        "service": "playwright",
        "endpoint": "http://localhost:8585/servers/playwright/sse",
        "command": ["node", "/home/administrator/projects/mcp/playwright/dist/index.js"],
        "tools": [
            {
                "name": "navigate",
                "mcp_name": "navigate",
                "description": "Navigate browser to a URL",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to navigate to"
                        }
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "screenshot",
                "mcp_name": "screenshot",
                "description": "Take a screenshot of the current page",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name for the screenshot file"
                        },
                        "fullPage": {
                            "type": "boolean",
                            "description": "Capture full page (default: false)",
                            "default": False
                        }
                    },
                    "required": ["name"]
                }
            },
            {
                "name": "click",
                "mcp_name": "click",
                "description": "Click an element on the page",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector of element to click"
                        }
                    },
                    "required": ["selector"]
                }
            },
            {
                "name": "fill",
                "mcp_name": "fill",
                "description": "Fill a form field with text",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector of input field"
                        },
                        "value": {
                            "type": "string",
                            "description": "Text to fill in the field"
                        }
                    },
                    "required": ["selector", "value"]
                }
            }
        ]
    },
    "timescaledb": {
        "service": "timescaledb",
        "endpoint": "http://localhost:8585/servers/timescaledb/sse",
        "docker_command": ["bash", "/home/administrator/projects/mcp/timescaledb/mcp-wrapper.sh"],
        "tools": [
            {
                "name": "list_hypertables",
                "mcp_name": "list_hypertables",
                "description": "List all TimescaleDB hypertables",
                "parameters_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "query_timeseries",
                "mcp_name": "query_timeseries",
                "description": "Query time-series data from TimescaleDB",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "SQL query for time-series data"
                        },
                        "database": {
                            "type": "string",
                            "description": "Database name (default: postgres)",
                            "default": "postgres"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "create_hypertable",
                "mcp_name": "create_hypertable",
                "description": "Create a new TimescaleDB hypertable",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "table_name": {
                            "type": "string",
                            "description": "Name of the table to convert"
                        },
                        "time_column": {
                            "type": "string",
                            "description": "Name of the time column"
                        },
                        "chunk_time_interval": {
                            "type": "string",
                            "description": "Chunk time interval (e.g., '1 day')",
                            "default": "1 day"
                        }
                    },
                    "required": ["table_name", "time_column"]
                }
            }
        ]
    }
}

def get_all_tools():
    """Get all tools from all services"""
    tools = []
    for service_name, service_def in TOOL_DEFINITIONS.items():
        for tool in service_def["tools"]:
            tool_with_service = tool.copy()
            tool_with_service["service"] = service_name
            tools.append(tool_with_service)
    return tools

def get_service_tools(service_name):
    """Get all tools for a specific service"""
    if service_name in TOOL_DEFINITIONS:
        return TOOL_DEFINITIONS[service_name]["tools"]
    return []

def find_tool(tool_name):
    """Find a tool definition by name across all services"""
    for service_name, service_def in TOOL_DEFINITIONS.items():
        for tool in service_def["tools"]:
            if tool["name"] == tool_name:
                return {
                    "service": service_name,
                    "endpoint": service_def["endpoint"],
                    "tool": tool
                }
    return None