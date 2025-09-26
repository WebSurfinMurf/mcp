import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.responses import Response
from sse_starlette.sse import EventSourceResponse

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("mcp-test-sse")

app = FastAPI(title="MCP Test SSE Server")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"]
)

@dataclass
class SessionState:
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


SESSIONS: Dict[str, SessionState] = {}

TOOL_DEFINITION: Dict[str, Any] = {
    "name": "echo",
    "description": "Echo back the provided text payload.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to echo back"
            }
        },
        "required": ["text"]
    }
}


async def _event_stream(request: Request, session_id: str, message_url: str, state: SessionState):
    logger.info("SSE connection opened for session %s", session_id)

    # Initial endpoint announcement
    yield {
        "event": "endpoint",
        "data": message_url,
    }
    logger.info("Session %s announced endpoint %s", session_id, message_url)

    try:
        while True:
            if await request.is_disconnected():
                logger.info("SSE client disconnected for session %s", session_id)
                break

            try:
                event = await asyncio.wait_for(state.queue.get(), timeout=15)
            except asyncio.TimeoutError:
                heartbeat = {
                    "event": "keepalive",
                    "data": "",
                }
                logger.debug("Session %s sending heartbeat", session_id)
                yield heartbeat
                continue

            logger.info("Session %s sending event: %s", session_id, event)
            yield event
    finally:
        SESSIONS.pop(session_id, None)
        logger.info("Session %s cleaned up", session_id)


@app.get("/sse")
async def sse_endpoint(request: Request):
    session_id = uuid.uuid4().hex
    state = SessionState()
    SESSIONS[session_id] = state

    message_url = str(request.url_for("handle_message")) + f"?sessionId={session_id}"
    return EventSourceResponse(_event_stream(request, session_id, message_url, state))


@app.post("/messages", name="handle_message")
async def handle_message(request: Request):
    session_id = request.query_params.get("sessionId")
    state = SESSIONS.get(session_id or "")
    if not session_id or state is None:
        raise HTTPException(status_code=404, detail="Unknown or expired session")

    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON body: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    logger.info("Session %s request: %s", session_id, json.dumps(payload))

    jsonrpc_id = payload.get("id")
    method = payload.get("method")

    result: Dict[str, Any]
    event_payload: Dict[str, Any] | None = None

    extra_events: list[Dict[str, Any]] = []

    if method == "initialize":
        requested_version = (
            payload.get("params", {}).get("protocolVersion")
            or "2025-06-18"
        )
        result = {
            "protocolVersion": requested_version,
            "serverInfo": {
                "name": "mcp-test-sse",
                "version": "0.1.0",
            },
            "capabilities": {
                "tools": {
                    "listChanged": True,
                },
            },
        }
        event_payload = {
            "event": "mcp",
            "data": json.dumps({
                "jsonrpc": "2.0",
                "id": jsonrpc_id,
                "result": result,
            }),
        }
        extra_events.append(
            {
                "event": "mcp",
                "data": json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "method": "notifications/tools/list_changed",
                        "params": {},
                    }
                ),
            }
        )
    elif method == "tools/list":
        result = {
            "tools": [TOOL_DEFINITION],
        }
        event_payload = {
            "event": "mcp",
            "data": json.dumps({
                "jsonrpc": "2.0",
                "id": jsonrpc_id,
                "result": result,
            }),
        }
    elif method == "tools/call":
        name = payload.get("params", {}).get("name")
        arguments = payload.get("params", {}).get("arguments", {}) or {}
        if name != TOOL_DEFINITION["name"]:
            return JSONResponse(
                status_code=200,
                content={
                    "jsonrpc": "2.0",
                    "id": jsonrpc_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown tool: {name}",
                    },
                },
            )
        text_value = arguments.get("text", "")
        result = {
            "content": [
                {
                    "type": "text",
                    "text": f"Echo: {text_value}",
                }
            ],
            "isError": False,
        }
        event_payload = {
            "event": "mcp",
            "data": json.dumps({
                "jsonrpc": "2.0",
                "id": jsonrpc_id,
                "result": result,
            }),
        }
    elif method == "ping":
        result = {
            "time": datetime.now(timezone.utc).isoformat(),
        }
    else:
        return JSONResponse(
            status_code=200,
            content={
                "jsonrpc": "2.0",
                "id": jsonrpc_id,
                "error": {
                    "code": -32601,
                    "message": f"Unsupported method: {method}",
                },
            },
        )

    if event_payload is None:
        event_payload = {
            "event": "mcp",
            "data": json.dumps({
                "jsonrpc": "2.0",
                "id": jsonrpc_id,
                "result": result,
            }),
        }

    logger.info("Session %s queueing event: %s", session_id, event_payload)
    await state.queue.put(event_payload)
    for extra in extra_events:
        logger.info("Session %s queueing extra event: %s", session_id, extra)
        await state.queue.put(extra)
    return Response(status_code=202)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "activeSessions": len(SESSIONS),
    }


@app.get("/")
async def root():
    return {
        "service": "mcp-test-sse",
        "documentation": "This is a protocol-compliant MCP SSE test server.",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
