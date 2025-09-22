
import asyncio
import json
import logging
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any

# --- Setup Logging ---
# Log to a file that will be mounted to the host
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("/app/logs/mcp_requests.log"),
        logging.StreamHandler()
    ]
)

app = FastAPI()

# --- MCP Data Models (simplified) ---
class ListToolsRequest(BaseModel):
    type: str = "ListToolsRequest"

class ExecuteToolRequest(BaseModel):
    type: str = "ExecuteToolRequest"
    tool_name: str
    parameters: Dict[str, Any]

class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]

class ListToolsResponse(BaseModel):
    type: str = "ListToolsResponse"
    tools: List[ToolDefinition]

class ExecuteToolResponse(BaseModel):
    type: str = "ExecuteToolResponse"
    stdout: str
    stderr: str = ""
    exit_code: int = 0

# --- Test Tool Definition ---
ECHO_TOOL = ToolDefinition(
    name="echo_tool",
    description="A simple tool that echoes back the input string.",
    parameters={
        "type": "object",
        "properties": {
            "input_string": {
                "type": "string",
                "description": "The string to echo back."
            }
        },
        "required": ["input_string"]
    }
)

# --- SSE Streaming Logic ---
async def sse_generator(request: Request):
    """
    Handles the Server-Sent Events (SSE) connection and MCP message processing.
    """
    # 1. Send the initial handshake event
    yield f"event: open\ndata: Connection established\n\n"
    logging.info("SSE connection opened.")

    # 2. Send the ListToolsResponse immediately after connection
    list_tools_response = ListToolsResponse(tools=[ECHO_TOOL])
    yield f"event: mcp\ndata: {list_tools_response.json()}\n\n"
    logging.info(f"Sent tool list: {list_tools_response.json()}")

    # 3. Listen for incoming messages
    while True:
        try:
            # Check if the client has disconnected
            if await request.is_disconnected():
                logging.info("Client disconnected.")
                break

            # Read the raw body of the request
            body_bytes = await request.body()
            if body_bytes:
                body_str = body_bytes.decode('utf-8')
                logging.info(f"Received raw payload: {body_str}")

                # Attempt to parse as JSON
                try:
                    payload = json.loads(body_str)
                    logging.info(f"Parsed JSON payload: {payload}")

                    # Check if it's an ExecuteToolRequest
                    if payload.get("type") == "ExecuteToolRequest":
                        tool_request = ExecuteToolRequest(**payload)
                        
                        logging.info(f"Executing tool: {tool_request.tool_name}")
                        
                        # Execute our simple echo tool
                        if tool_request.tool_name == "echo_tool":
                            input_str = tool_request.parameters.get("input_string", "No input provided")
                            response_stdout = f"Successfully echoed: {input_str}"
                            
                            tool_response = ExecuteToolResponse(
                                stdout=response_stdout
                            )
                            
                            yield f"event: mcp\ndata: {tool_response.json()}\n\n"
                            logging.info(f"Sent tool response: {tool_response.json()}")

                except json.JSONDecodeError:
                    logging.error(f"Could not decode JSON from payload: {body_str}")
            
            # Small delay to prevent a tight loop
            await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            logging.info("Connection cancelled.")
            break
        except Exception as e:
            logging.error(f"An error occurred: {e}", exc_info=True)
            break

@app.get("/sse")
async def sse_endpoint(request: Request):
    return StreamingResponse(sse_generator(request), media_type="text/event-stream")

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
