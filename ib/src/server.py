"""
MCP IB (Interactive Brokers) Server
Provides market data and portfolio operations via MCP endpoint

Uses a process pool to handle concurrent requests efficiently.
Each worker maintains its own IB connection with a unique client ID.

Enhanced with:
- Active IB connection health checking
- Circuit breaker pattern for failure management
- Background health monitoring with auto-restart
- Retry with exponential backoff
"""
import os
import json
import asyncio
import time
from dataclasses import dataclass, field
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
POOL_SIZE = int(os.getenv("IB_POOL_SIZE", "3"))
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))


@dataclass
class CircuitBreaker:
    """Circuit breaker to prevent cascading failures"""
    failure_threshold: int = 3
    recovery_timeout: int = 60
    failure_count: int = 0
    last_failure: float = 0
    state: str = "closed"  # closed, open, half-open
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def record_success(self):
        """Record a successful call"""
        async with self._lock:
            self.failure_count = 0
            if self.state == "half-open":
                logger.info("Circuit breaker: CLOSED (recovered)")
                self.state = "closed"

    async def record_failure(self):
        """Record a failed call"""
        async with self._lock:
            self.failure_count += 1
            self.last_failure = time.time()
            if self.failure_count >= self.failure_threshold and self.state == "closed":
                self.state = "open"
                logger.error(f"Circuit breaker: OPEN after {self.failure_count} failures")

    async def can_execute(self) -> bool:
        """Check if we can execute a request"""
        async with self._lock:
            if self.state == "closed":
                return True
            if self.state == "open":
                if time.time() - self.last_failure > self.recovery_timeout:
                    self.state = "half-open"
                    logger.info("Circuit breaker: HALF-OPEN (attempting recovery)")
                    return True
                return False
            # half-open: allow one request through
            return True

    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status"""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_ago": int(time.time() - self.last_failure) if self.last_failure else None,
            "recovery_in": max(0, int(self.recovery_timeout - (time.time() - self.last_failure))) if self.state == "open" else None
        }


@dataclass
class IBWorker:
    """A single IB MCP subprocess worker"""
    worker_id: int
    client_id: int
    process: Optional[asyncio.subprocess.Process] = None
    initialized: bool = False
    lock: asyncio.Lock = None
    last_successful_call: float = 0
    consecutive_failures: int = 0
    ib_connected: bool = False

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
            self.consecutive_failures = 0
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
                self.ib_connected = False

    def is_alive(self) -> bool:
        """Check if process is still running"""
        return self.process is not None and self.process.returncode is None

    async def check_ib_connection(self) -> bool:
        """Actually test IB connectivity by making a lightweight call"""
        if not self.is_alive():
            self.ib_connected = False
            return False

        try:
            # Use get_account_summary as a lightweight connectivity test
            test_request = {
                "jsonrpc": "2.0",
                "id": "health_check",
                "method": "tools/call",
                "params": {"name": "get_account_summary", "arguments": {}}
            }

            self.process.stdin.write(json.dumps(test_request).encode() + b'\n')
            await self.process.stdin.drain()

            response_line = await asyncio.wait_for(
                self.process.stdout.readline(),
                timeout=10.0
            )

            if not response_line:
                self.ib_connected = False
                return False

            response = json.loads(response_line.decode().strip())

            # Check for "Not connected" or other IB errors
            if "result" in response:
                content = response["result"].get("content", [])
                if content:
                    text = content[0].get("text", "") if isinstance(content[0], dict) else str(content[0])
                    if "Not connected" in text or "Cannot connect" in text:
                        logger.warning(f"Worker {self.worker_id}: IB not connected")
                        self.ib_connected = False
                        return False

            self.ib_connected = True
            self.last_successful_call = time.time()
            return True

        except asyncio.TimeoutError:
            logger.warning(f"Worker {self.worker_id}: Health check timeout")
            self.ib_connected = False
            return False
        except Exception as e:
            logger.warning(f"Worker {self.worker_id}: Health check error - {e}")
            self.ib_connected = False
            return False

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

            response = json.loads(response_line.decode().strip())

            # Check if this was a successful IB call
            if "result" in response:
                content = response["result"].get("content", [])
                if content:
                    text = content[0].get("text", "") if isinstance(content[0], dict) else str(content[0])
                    if "Not connected" in text or "Cannot connect" in text:
                        self.ib_connected = False
                        self.consecutive_failures += 1
                        return response

            # Success
            self.consecutive_failures = 0
            self.last_successful_call = time.time()
            self.ib_connected = True
            return response

        except asyncio.TimeoutError:
            logger.error(f"Worker {self.worker_id}: Timeout")
            self.consecutive_failures += 1
            await self.stop()
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": "Timeout waiting for IB response"},
                "id": request_data.get("id")
            }
        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Error - {e}")
            self.consecutive_failures += 1
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
        self._health_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """Initialize the pool - make all workers available"""
        if self._initialized:
            return
        for worker in self.workers:
            await self._available.put(worker)
        self._initialized = True
        logger.info(f"Worker pool initialized with {self.size} workers")

    async def start_health_monitor(self) -> None:
        """Start background health monitoring"""
        self._health_task = asyncio.create_task(self._health_monitor())
        logger.info(f"Health monitor started (interval: {HEALTH_CHECK_INTERVAL}s)")

    async def _health_monitor(self) -> None:
        """Background task to monitor worker health and restart if needed"""
        while True:
            try:
                await asyncio.sleep(HEALTH_CHECK_INTERVAL)

                for worker in self.workers:
                    if worker.is_alive():
                        # Check actual IB connectivity
                        async with worker.lock:
                            connected = await worker.check_ib_connection()
                            if not connected:
                                logger.warning(f"Worker {worker.worker_id}: IB connection lost, restarting...")
                                await worker.stop()
                                # Worker will auto-restart on next request

                    # Log worker status
                    if worker.consecutive_failures > 0:
                        logger.warning(f"Worker {worker.worker_id}: {worker.consecutive_failures} consecutive failures")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor error: {e}")

    @asynccontextmanager
    async def acquire(self):
        """Acquire a worker from the pool"""
        worker = await self._available.get()
        try:
            yield worker
        finally:
            await self._available.put(worker)

    async def shutdown(self) -> None:
        """Stop all workers and health monitor"""
        logger.info("Shutting down worker pool")
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        for worker in self.workers:
            await worker.stop()

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        alive = sum(1 for w in self.workers if w.is_alive())
        ib_connected = sum(1 for w in self.workers if w.ib_connected)
        return {
            "pool_size": self.size,
            "workers_alive": alive,
            "workers_ib_connected": ib_connected,
            "workers_available": self._available.qsize(),
            "workers": [
                {
                    "id": w.worker_id,
                    "client_id": w.client_id,
                    "alive": w.is_alive(),
                    "initialized": w.initialized,
                    "ib_connected": w.ib_connected,
                    "consecutive_failures": w.consecutive_failures,
                    "last_success_ago": int(time.time() - w.last_successful_call) if w.last_successful_call else None
                }
                for w in self.workers
            ]
        }


# Global instances
pool: Optional[IBWorkerPool] = None
circuit_breaker = CircuitBreaker()


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


def is_ib_not_connected_error(response: Dict[str, Any]) -> bool:
    """Check if response indicates IB is not connected"""
    if "result" in response:
        content = response["result"].get("content", [])
        if content:
            text = content[0].get("text", "") if isinstance(content[0], dict) else str(content[0])
            return "Not connected" in text or "Cannot connect" in text
    return False


async def send_to_ib_mcp(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Send request to IB MCP via worker pool with retry logic"""
    global pool, circuit_breaker

    # Handle initialize request without using a worker
    if request_data.get("method") == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_data.get("id"),
            "result": INIT_RESPONSE
        }

    # Check circuit breaker
    if not await circuit_breaker.can_execute():
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": f"Circuit breaker OPEN - IB unavailable. Recovery in {circuit_breaker.get_status()['recovery_in']}s"
            },
            "id": request_data.get("id")
        }

    # Retry loop with exponential backoff
    last_response = None
    for attempt in range(MAX_RETRIES + 1):
        async with pool.acquire() as worker:
            async with worker.lock:
                response = await worker.send_request(request_data)
                last_response = response

                # Check if IB not connected
                if is_ib_not_connected_error(response):
                    await circuit_breaker.record_failure()

                    if attempt < MAX_RETRIES:
                        logger.warning(f"IB not connected, restarting worker (attempt {attempt + 1}/{MAX_RETRIES + 1})")
                        await worker.stop()
                        backoff = 2 ** attempt
                        await asyncio.sleep(backoff)
                        continue

                    # All retries exhausted
                    return response

                # Check for other errors
                if "error" in response:
                    await circuit_breaker.record_failure()
                    return response

                # Success!
                await circuit_breaker.record_success()
                return response

    return last_response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global pool
    logger.info(f"Starting MCP IB Server with {POOL_SIZE} workers")
    logger.info(f"Connecting to {IB_HOST}:{IB_PORT}, base client_id={IB_CLIENT_ID_BASE}")
    logger.info(f"Health check interval: {HEALTH_CHECK_INTERVAL}s, Max retries: {MAX_RETRIES}")

    pool = IBWorkerPool(size=POOL_SIZE, base_client_id=IB_CLIENT_ID_BASE)
    await pool.initialize()
    await pool.start_health_monitor()

    yield

    logger.info("Shutting down MCP IB Server")
    await pool.shutdown()


app = FastAPI(title="MCP IB Server", version="2.1.0", lifespan=lifespan)


@app.get("/health")
async def health_check():
    """Health check endpoint with real IB connectivity status"""
    pool_stats = pool.get_stats() if pool else None

    # Determine overall status
    if pool_stats:
        ib_connected = pool_stats["workers_ib_connected"] > 0
        workers_alive = pool_stats["workers_alive"] > 0
    else:
        ib_connected = False
        workers_alive = False

    cb_status = circuit_breaker.get_status()

    if cb_status["state"] == "open":
        status = "unhealthy"
    elif not workers_alive:
        status = "unhealthy"
    elif not ib_connected:
        status = "degraded"
    else:
        status = "healthy"

    return {
        "status": status,
        "ib_connected": ib_connected,
        "service": MCP_SERVER_NAME,
        "ib_host": IB_HOST,
        "ib_port": IB_PORT,
        "circuit_breaker": cb_status,
        "pool": pool_stats
    }


@app.post("/mcp")
async def mcp_endpoint(request: MCPRequest):
    """HTTP POST endpoint for MCP requests"""
    return await send_to_ib_mcp(request.dict())


@app.post("/restart-workers")
async def restart_workers():
    """Force restart all workers"""
    if pool:
        for worker in pool.workers:
            async with worker.lock:
                await worker.stop()
        return {"message": "All workers stopped. They will restart on next request."}
    return {"error": "Pool not initialized"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
