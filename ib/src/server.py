"""
MCP IB (Interactive Brokers) Server
Provides market data and portfolio operations via MCP endpoint

Uses a process pool to handle concurrent requests efficiently.
Each worker maintains its own IB connection with a unique client ID.
"""
import os
import json
import asyncio
from dataclasses import dataclass
from typing import Dict, Any, Optional, Union, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from pydantic import BaseModel
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
MCP_SERVER_NAME = os.getenv("MCP_SERVER_NAME", "ib")
IB_HOST = os.getenv("IB_HOST", "mcp-ib-gateway")
IB_PORT = os.getenv("IB_PORT", "4002")
IB_CLIENT_ID_BASE = int(os.getenv("IB_CLIENT_ID", "1"))
POOL_SIZE = int(os.getenv("IB_POOL_SIZE", "3"))  # Default 3 workers


@dataclass
class IBWorker:
    """A single IB MCP subprocess worker"""
    worker_id: int
    client_id: int
    process: Optional[asyncio.subprocess.Process] = None
    initialized: bool = False
    lock: asyncio.Lock = None

    def __post_init__(self):
        self.lock = asyncio.Lock()

    async def start(self) -> bool:
        """Start the subprocess and initialize MCP protocol"""
        if self.process is not None and self.process.returncode is None:
            return True  # Already running

        logger.info(f"Worker {self.worker_id}: Starting IB MCP (client_id={self.client_id})")
        try:
            self.process = await asyncio.create_subprocess_exec(
                "python3", "-m", "ib_mcp.server",
                "--host", IB_HOST,
                "--port", IB_PORT,
                "--client-id", str(self.client_id),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Send MCP initialize
            init_msg = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": f"mcp-ib-http-{self.worker_id}", "version": "1.0.0"}
                },
                "id": "init"
            }
            self.process.stdin.write(json.dumps(init_msg).encode() + b'\n')
            await self.process.stdin.drain()

            init_response = await asyncio.wait_for(
                self.process.stdout.readline(),
                timeout=10.0
            )
            logger.info(f"Worker {self.worker_id}: Initialized - {init_response.decode().strip()[:100]}")

            # Send initialized notification
            notif = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
            self.process.stdin.write(json.dumps(notif).encode() + b'\n')
            await self.process.stdin.drain()

            self.initialized = True
            return True

        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Failed to start - {e}")
            await self.stop()
            return False

    async def stop(self) -> None:
        """Stop the subprocess"""
        if self.process is not None:
            logger.info(f"Worker {self.worker_id}: Stopping")
            try:
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    self.process.kill()
                    await self.process.wait()
            except ProcessLookupError:
                pass
            except Exception as e:
                logger.error(f"Worker {self.worker_id}: Error stopping - {e}")
            finally:
                self.process = None
                self.initialized = False

    def is_alive(self) -> bool:
        """Check if process is still running"""
        return self.process is not None and self.process.returncode is None

    async def send_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request and get response (must hold lock)"""
        if not self.is_alive():
            if not await self.start():
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": "Failed to start IB worker"},
                    "id": request_data.get("id")
                }

        try:
            self.process.stdin.write(json.dumps(request_data).encode() + b'\n')
            await self.process.stdin.drain()

            response_line = await asyncio.wait_for(
                self.process.stdout.readline(),
                timeout=30.0
            )

            if not response_line:
                raise Exception("Process closed unexpectedly")

            return json.loads(response_line.decode().strip())

        except asyncio.TimeoutError:
            logger.error(f"Worker {self.worker_id}: Timeout")
            await self.stop()
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": "Timeout waiting for IB response"},
                "id": request_data.get("id")
            }
        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Error - {e}")
            await self.stop()
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)},
                "id": request_data.get("id")
            }


class IBWorkerPool:
    """Pool of IB MCP workers for concurrent request handling"""

    def __init__(self, size: int, base_client_id: int):
        self.size = size
        self.workers: List[IBWorker] = [
            IBWorker(worker_id=i, client_id=base_client_id + i)
            for i in range(size)
        ]
        self._available = asyncio.Queue()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the pool - make all workers available"""
        if self._initialized:
            return
        for worker in self.workers:
            await self._available.put(worker)
        self._initialized = True
        logger.info(f"Worker pool initialized with {self.size} workers")

    @asynccontextmanager
    async def acquire(self):
        """Acquire a worker from the pool"""
        worker = await self._available.get()
        try:
            yield worker
        finally:
            await self._available.put(worker)

    async def shutdown(self) -> None:
        """Stop all workers"""
        logger.info("Shutting down worker pool")
        for worker in self.workers:
            await worker.stop()

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        alive = sum(1 for w in self.workers if w.is_alive())
        return {
            "pool_size": self.size,
            "workers_alive": alive,
            "workers_available": self._available.qsize(),
            "workers": [
                {"id": w.worker_id, "client_id": w.client_id, "alive": w.is_alive(), "initialized": w.initialized}
                for w in self.workers
            ]
        }


# Global pool instance
pool: Optional[IBWorkerPool] = None


class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None


class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None


# Cached initialize response (same for all workers)
INIT_RESPONSE = {
    "protocolVersion": "2024-11-05",
    "capabilities": {
        "experimental": {},
        "prompts": {"listChanged": False},
        "resources": {"subscribe": False, "listChanged": False},
        "tools": {"listChanged": True}
    },
    "serverInfo": {"name": "IBKR MCP Server", "version": "1.16.0"},
    "instructions": "Fetch portfolio and market data using IBKR TWS APIs."
}


async def send_to_ib_mcp(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Send request to IB MCP via worker pool"""
    global pool

    # Handle initialize request without using a worker
    if request_data.get("method") == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_data.get("id"),
            "result": INIT_RESPONSE
        }

    # Acquire worker and send request
    async with pool.acquire() as worker:
        async with worker.lock:
            return await worker.send_request(request_data)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global pool
    logger.info(f"Starting MCP IB Server with {POOL_SIZE} workers")
    logger.info(f"Connecting to {IB_HOST}:{IB_PORT}, base client_id={IB_CLIENT_ID_BASE}")

    pool = IBWorkerPool(size=POOL_SIZE, base_client_id=IB_CLIENT_ID_BASE)
    await pool.initialize()

    yield

    logger.info("Shutting down MCP IB Server")
    await pool.shutdown()


app = FastAPI(title="MCP IB Server", version="2.0.0", lifespan=lifespan)


@app.get("/health")
async def health_check():
    """Health check endpoint with pool stats"""
    return {
        "status": "healthy",
        "service": MCP_SERVER_NAME,
        "ib_host": IB_HOST,
        "ib_port": IB_PORT,
        "pool": pool.get_stats() if pool else None
    }


@app.post("/mcp")
async def mcp_endpoint(request: MCPRequest):
    """HTTP POST endpoint for MCP requests"""
    return await send_to_ib_mcp(request.dict())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
