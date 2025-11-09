"""
Open WebUI Custom Functions for MCP Code Executor

Installation:
1. Go to Open WebUI → Workspace → Functions
2. Click "+ Add Function"
3. Paste each function below
4. Enable the function

Usage:
Once installed, these functions are automatically available to Claude in conversations.
"""

# ============================================================================
# Function 1: Execute MCP Workflow
# ============================================================================

"""
title: Execute MCP Workflow
author: Claude Code
version: 1.0.0
description: Execute TypeScript code with access to all 63 MCP tools
required_open_webui_version: 0.3.0
"""

import requests
from typing import Optional
from pydantic import BaseModel, Field


class Action:
    class Valves(BaseModel):
        CODE_EXECUTOR_URL: str = Field(
            default="http://mcp-code-executor:3000",
            description="URL of the MCP code executor service"
        )
        EXECUTION_TIMEOUT: int = Field(
            default=30000,
            description="Execution timeout in milliseconds"
        )

    def __init__(self):
        self.valves = self.Valves()

    async def action(
        self,
        body: dict,
        __user__=None,
        __event_emitter__=None,
    ) -> Optional[dict]:
        """Execute TypeScript code with MCP tool access"""

        # Extract the code from user's message
        user_message = body.get("messages", [])[-1].get("content", "")

        # Check if this is a code execution request
        if not any(keyword in user_message.lower() for keyword in ["execute", "run", "workflow", "mcp tools"]):
            return None  # Let normal conversation flow continue

        # Emit status
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "Executing workflow with MCP tools...", "done": False},
                }
            )

        # Extract code block from message (assumes ```typescript or ```javascript block)
        code = None
        if "```" in user_message:
            parts = user_message.split("```")
            if len(parts) >= 3:
                code_block = parts[1]
                # Remove language identifier if present
                if code_block.startswith("typescript\n") or code_block.startswith("javascript\n"):
                    code = "\n".join(code_block.split("\n")[1:])
                else:
                    code = code_block

        if not code:
            return {
                "error": "No code block found. Please provide TypeScript code in ```typescript code blocks."
            }

        # Execute the code
        try:
            response = requests.post(
                f"{self.valves.CODE_EXECUTOR_URL}/execute",
                json={"code": code, "timeout": self.valves.EXECUTION_TIMEOUT},
                timeout=self.valves.EXECUTION_TIMEOUT / 1000 + 5,  # Add 5s buffer
            )

            if not response.ok:
                error_data = response.json()
                return {
                    "error": f"Execution failed: {error_data.get('error', error_data.get('message', 'Unknown error'))}"
                }

            result = response.json()

            # Emit completion
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": "Workflow executed successfully", "done": True},
                    }
                )

            # Format response
            if result.get("error"):
                return {
                    "output": f"❌ Error:\n{result['error']}\n\n⏱️ Execution time: {result['executionTime']}ms"
                }
            else:
                metrics = result.get("metrics", {})
                return {
                    "output": (
                        f"✅ Output:\n{result['output']}\n\n"
                        f"⏱️ Execution: {result['executionTime']}ms | "
                        f"📊 {metrics.get('outputBytes', 0)} bytes (~{metrics.get('tokensEstimate', 0)} tokens)"
                    )
                }

        except requests.exceptions.Timeout:
            return {"error": "Execution timeout exceeded"}
        except Exception as e:
            return {"error": f"Execution error: {str(e)}"}


# ============================================================================
# Function 2: Search MCP Tools
# ============================================================================

"""
title: Search MCP Tools
author: Claude Code
version: 1.0.0
description: Search available MCP tools with progressive disclosure
required_open_webui_version: 0.3.0
"""

import requests
from typing import Optional
from pydantic import BaseModel, Field


class Action:
    class Valves(BaseModel):
        CODE_EXECUTOR_URL: str = Field(
            default="http://mcp-code-executor:3000",
            description="URL of the MCP code executor service"
        )

    def __init__(self):
        self.valves = self.Valves()

    async def action(
        self,
        body: dict,
        __user__=None,
        __event_emitter__=None,
    ) -> Optional[dict]:
        """Search MCP tools with progressive disclosure"""

        user_message = body.get("messages", [])[-1].get("content", "")

        # Check if this is a tool search request
        if not any(keyword in user_message.lower() for keyword in ["search tools", "find tools", "list tools", "what tools"]):
            return None

        # Parse search parameters from message
        query = None
        server = None
        detail = "name"  # Default to minimal tokens

        # Simple keyword extraction
        if "database" in user_message.lower():
            query = "database"
        if "filesystem" in user_message.lower():
            server = "filesystem"
        if "full" in user_message.lower() or "complete" in user_message.lower():
            detail = "full"
        elif "description" in user_message.lower() or "details" in user_message.lower():
            detail = "description"

        # Emit status
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "Searching MCP tools...", "done": False},
                }
            )

        # Build query params
        params = {"detail": detail}
        if query:
            params["query"] = query
        if server:
            params["server"] = server

        # Search tools
        try:
            response = requests.get(
                f"{self.valves.CODE_EXECUTOR_URL}/tools/search",
                params=params,
                timeout=5,
            )

            if not response.ok:
                return {"error": f"Search failed: {response.status_code}"}

            result = response.json()

            # Emit completion
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": f"Found {result.get('count', 0)} tools", "done": True},
                    }
                )

            # Format results
            tools = result.get("results", [])
            output = f"## MCP Tools ({result.get('count', 0)} found)\n\n"

            for tool in tools:
                if detail == "name":
                    output += f"- `{tool['name']}`\n"
                elif detail == "description":
                    output += f"### `{tool['name']}`\n{tool.get('description', 'No description')}\n\n"
                else:  # full
                    output += f"### `{tool['name']}`\n"
                    output += f"**Description:** {tool.get('description', 'No description')}\n"
                    output += f"**Signature:** `{tool.get('signature', 'Unknown')}`\n"
                    if tool.get("source"):
                        output += f"\n```typescript\n{tool['source']}\n```\n"
                    output += "\n"

            # Add token savings info
            savings = result.get("tokenSavings", {})
            if savings:
                output += f"\n💡 **Token efficiency:** {savings.get('currentLevel', detail)} level"

            return {"output": output}

        except Exception as e:
            return {"error": f"Search error: {str(e)}"}


# ============================================================================
# Function 3: List All MCP Tools
# ============================================================================

"""
title: List MCP Tools
author: Claude Code
version: 1.0.0
description: List all available MCP tools organized by server
required_open_webui_version: 0.3.0
"""

import requests
from typing import Optional
from pydantic import BaseModel, Field


class Action:
    class Valves(BaseModel):
        CODE_EXECUTOR_URL: str = Field(
            default="http://mcp-code-executor:3000",
            description="URL of the MCP code executor service"
        )

    def __init__(self):
        self.valves = self.Valves()

    async def action(
        self,
        body: dict,
        __user__=None,
        __event_emitter__=None,
    ) -> Optional[dict]:
        """List all MCP tools organized by server"""

        user_message = body.get("messages", [])[-1].get("content", "")

        # Only trigger on explicit list request
        if "list all tools" not in user_message.lower() and "show all tools" not in user_message.lower():
            return None

        # Get health data with tool inventory
        try:
            response = requests.get(
                f"{self.valves.CODE_EXECUTOR_URL}/health",
                timeout=5,
            )

            if not response.ok:
                return {"error": "Failed to fetch tool list"}

            health = response.json()
            tools_by_server = health.get("toolsByServer", {})

            # Format output
            output = f"## Available MCP Tools ({health.get('totalTools', 0)} total)\n\n"

            for server, tools in tools_by_server.items():
                output += f"### 📦 {server} ({len(tools)} tools)\n"
                for tool in tools:
                    output += f"- `{tool}`\n"
                output += "\n"

            output += f"\n💡 Use 'search tools' to find specific tools with progressive disclosure\n"
            output += f"💡 Use 'execute workflow' to run TypeScript code with these tools\n"

            return {"output": output}

        except Exception as e:
            return {"error": f"Error listing tools: {str(e)}"}
