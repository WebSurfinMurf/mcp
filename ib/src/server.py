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
- Gateway control (login/logout) for TWS session management
"""
import os
import json
import asyncio
import time
import socket
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

# Gateway control configuration
# Uses Docker to control the gateway container
GATEWAY_CONTAINER = os.getenv("GATEWAY_CONTAINER", "mcp-ib-gateway")
DOCKER_SOCKET = "/var/run/docker.sock"


async def docker_command(action: str, container: str = None) -> Dict[str, Any]:
    """Execute a Docker command on the gateway container"""
    import subprocess
    container = container or GATEWAY_CONTAINER

    try:
        if action == "stop":
            cmd = ["docker", "stop", container]
        elif action == "start":
            cmd = ["docker", "start", container]
        elif action == "restart":
            cmd = ["docker", "restart", container]
        elif action == "status":
            cmd = ["docker", "inspect", "-f", "{{.State.Status}}", container]
        else:
            return {"success": False, "error": f"Unknown action: {action}"}

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            return {
                "success": True,
                "action": action,
                "container": container,
                "output": result.stdout.strip()
            }
        else:
            return {
                "success": False,
                "action": action,
                "container": container,
                "error": result.stderr.strip()
            }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Docker {action} timed out"}
    except FileNotFoundError:
        return {"success": False, "error": "Docker not available in container"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def check_gateway_status() -> Dict[str, Any]:
    """Check if gateway is logged in and responsive"""
    # Check Docker container status
    docker_status = await docker_command("status")
    container_running = docker_status.get("output") == "running" if docker_status["success"] else False

    # Try to connect to IB API port (4004 for paper via socat)
    api_port_open = False
    if container_running:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(IB_HOST, int(IB_PORT)),
                timeout=3.0
            )
            writer.close()
            await writer.wait_closed()
            api_port_open = True
        except:
            pass

    # Check if we can make actual IB calls
    pool_stats = pool.get_stats() if pool else None
    ib_connected = pool_stats["workers_ib_connected"] > 0 if pool_stats else False

    # Determine overall gateway status
    if ib_connected and api_port_open:
        status = "connected"
    elif api_port_open and not ib_connected:
        status = "api_ready"  # Gateway up but workers not connected
    elif container_running and not api_port_open:
        status = "starting"  # Container running but API not ready
    else:
        status = "disconnected"

    return {
        "status": status,
        "container_running": container_running,
        "api_port_open": api_port_open,
        "ib_connected": ib_connected,
        "gateway_container": GATEWAY_CONTAINER,
        "api_host": IB_HOST,
        "api_port": IB_PORT
    }


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
    # Track restarts for backoff (don't reset on start)
    restart_count: int = 0
    last_restart_time: float = 0

    def __post_init__(self):
        self.lock = asyncio.Lock()

    def should_restart(self) -> bool:
        """Check if enough time has passed for backoff-based restart."""
        if self.restart_count == 0:
            return True
        # Exponential backoff: 5s, 10s, 20s, 40s, max 60s
        backoff = min(5 * (2 ** (self.restart_count - 1)), 60)
        elapsed = time.time() - self.last_restart_time
        return elapsed >= backoff

    async def start(self) -> bool:
        """Start the subprocess and initialize MCP protocol"""
        if self.process is not None and self.process.returncode is None:
            return True  # Already running

        # Track restart for backoff
        self.restart_count += 1
        self.last_restart_time = time.time()
        logger.info(f"Worker {self.worker_id}: Starting IB MCP (client_id={self.client_id}, restart #{self.restart_count})")
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
            # Don't reset consecutive_failures here - only reset when IB actually connects
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
            # Reset failure/restart counters on successful IB check
            self.consecutive_failures = 0
            self.restart_count = 0
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
        """Background task to monitor worker health and auto-reconnect gateway if needed"""
        consecutive_disconnects = 0

        while True:
            try:
                await asyncio.sleep(HEALTH_CHECK_INTERVAL)

                workers_connected = 0
                workers_needing_restart = []

                for i, worker in enumerate(self.workers):
                    # Stagger checks to avoid IB connection storms
                    if i > 0:
                        await asyncio.sleep(2)

                    if worker.is_alive():
                        # Check actual IB connectivity
                        async with worker.lock:
                            connected = await worker.check_ib_connection()
                            if connected:
                                workers_connected += 1
                            else:
                                # Increment failure count but don't restart immediately
                                worker.consecutive_failures += 1
                                logger.warning(f"Worker {worker.worker_id}: IB check failed ({worker.consecutive_failures} consecutive)")

                                # Only restart after 2+ consecutive failures AND backoff elapsed
                                if worker.consecutive_failures >= 2 and worker.should_restart():
                                    workers_needing_restart.append(worker)
                    else:
                        # Worker not alive - check if we should restart with backoff
                        if worker.should_restart():
                            workers_needing_restart.append(worker)

                    # Log persistent failures
                    if worker.restart_count >= 3:
                        logger.warning(f"Worker {worker.worker_id}: {worker.restart_count} restart attempts, backing off")

                # Restart workers that need it (one at a time with delay)
                for worker in workers_needing_restart:
                    async with worker.lock:
                        backoff = min(5 * (2 ** (worker.restart_count)), 60) if worker.restart_count > 0 else 5
                        logger.info(f"Worker {worker.worker_id}: Restarting (attempt #{worker.restart_count + 1}, next backoff {backoff}s)")
                        await worker.stop()
                        # Small delay before restart to let IB settle
                        await asyncio.sleep(3)

                # Auto-reconnect gateway if all workers disconnected for 2+ checks
                if workers_connected == 0:
                    consecutive_disconnects += 1
                    logger.warning(f"All workers disconnected ({consecutive_disconnects} consecutive checks)")

                    if consecutive_disconnects >= 2:
                        logger.info("Auto-reconnecting gateway after sustained disconnection...")
                        await self._auto_reconnect_gateway()
                        consecutive_disconnects = 0
                        # Reset all worker restart counts after gateway reconnect
                        for worker in self.workers:
                            worker.restart_count = 0
                            worker.consecutive_failures = 0
                else:
                    consecutive_disconnects = 0

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor error: {e}")

    async def _auto_reconnect_gateway(self) -> None:
        """Auto-reconnect the gateway container"""
        try:
            # Stop all workers first
            for worker in self.workers:
                async with worker.lock:
                    await worker.stop()

            # Restart gateway container
            result = await docker_command("restart")
            if result["success"]:
                logger.info("Gateway restart initiated by health monitor")
                # Wait for gateway to come up
                await asyncio.sleep(30)
            else:
                logger.error(f"Gateway auto-restart failed: {result.get('error')}")
        except Exception as e:
            logger.error(f"Auto-reconnect error: {e}")

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
                    "restart_count": w.restart_count,
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


# ============================================================================
# Gateway Control Endpoints
# ============================================================================

@app.get("/gateway/status")
async def gateway_status():
    """
    Get IB Gateway connection status.

    Returns:
        status: "connected", "api_ready", "starting", or "disconnected"
        api_port_open: Whether the IB API port is accepting connections
        ibc_responsive: Whether the IBC command server is responding
        ib_connected: Whether workers have active IB connections
    """
    return await check_gateway_status()


@app.post("/gateway/logout")
async def gateway_logout():
    """
    Logout from IB Gateway by stopping the gateway container.

    This frees up the IB session so you can use TWS on another machine.
    To login again, use POST /gateway/login
    """
    logger.info("Gateway logout requested")

    # First stop all workers
    if pool:
        for worker in pool.workers:
            async with worker.lock:
                await worker.stop()
        logger.info("All workers stopped")

    # Stop the gateway container
    result = await docker_command("stop")

    if result["success"]:
        logger.info("Gateway container stopped")
        return {
            "success": True,
            "message": "Gateway stopped. IB session is now free for TWS.",
            "note": "Use POST /gateway/login to restart the gateway when ready."
        }
    else:
        logger.error(f"Failed to stop gateway: {result['error']}")
        return {
            "success": False,
            "message": "Failed to stop gateway container",
            "error": result.get("error")
        }


@app.post("/gateway/login")
async def gateway_login():
    """
    Login to IB Gateway by starting/restarting the gateway container.

    This will start the gateway and it will auto-authenticate with saved credentials.
    """
    logger.info("Gateway login requested")

    # Check current status
    status = await check_gateway_status()

    if status["status"] == "connected":
        return {
            "success": True,
            "message": "Gateway is already connected",
            "status": status
        }

    # Start or restart the gateway container
    if status["container_running"]:
        logger.info("Container running but not connected, restarting")
        result = await docker_command("restart")
    else:
        logger.info("Container not running, starting")
        result = await docker_command("start")

    if result["success"]:
        # Stop workers so they reconnect fresh
        if pool:
            for worker in pool.workers:
                async with worker.lock:
                    await worker.stop()

        return {
            "success": True,
            "message": "Gateway started. Authentication in progress.",
            "note": "Wait 30-60 seconds for gateway to authenticate, then check /gateway/status"
        }
    else:
        return {
            "success": False,
            "message": "Failed to start gateway container",
            "error": result.get("error")
        }


@app.post("/gateway/reconnect")
async def gateway_reconnect():
    """
    Force reconnection by restarting the gateway container.

    Useful when connection is stale or having issues.
    """
    logger.info("Gateway reconnect requested")

    # Stop all workers first
    if pool:
        for worker in pool.workers:
            async with worker.lock:
                await worker.stop()

    # Restart the gateway container
    result = await docker_command("restart")

    return {
        "success": result["success"],
        "message": "Gateway restart initiated. Workers stopped.",
        "note": "Wait 30-60 seconds for gateway to reconnect, then check /gateway/status",
        "docker_result": result
    }


@app.post("/gateway/ensure-ready")
async def gateway_ensure_ready(timeout: int = 90):
    """
    Ensure gateway is connected before making requests.

    - Returns immediately (200) if already connected
    - Auto-reconnects and waits if disconnected
    - Returns error (503) if reconnect fails within timeout

    Use this before making IB API calls to ensure connection is ready.
    Client code example:
        requests.post("http://localhost:48012/gateway/ensure-ready", timeout=90)
        response = requests.post("http://localhost:48012/mcp", json={...})
    """
    # Quick check - if already connected, return immediately
    status = await check_gateway_status()
    if status["status"] == "connected":
        return {
            "ready": True,
            "message": "Gateway already connected",
            "waited": 0
        }

    logger.info("Gateway not ready, triggering reconnect...")

    # Not connected - trigger reconnect
    if pool:
        for worker in pool.workers:
            async with worker.lock:
                await worker.stop()

    # Start or restart gateway
    if status["container_running"]:
        await docker_command("restart")
    else:
        await docker_command("start")

    # Wait for connection with timeout
    start_time = time.time()
    max_wait = min(timeout, 120)  # Cap at 2 minutes

    while time.time() - start_time < max_wait:
        await asyncio.sleep(2)  # Check every 2 seconds
        status = await check_gateway_status()
        if status["status"] == "connected":
            waited = int(time.time() - start_time)
            logger.info(f"Gateway ready after {waited}s")
            return {
                "ready": True,
                "message": f"Gateway connected after {waited}s",
                "waited": waited
            }

    # Timeout - still not connected
    waited = int(time.time() - start_time)
    logger.error(f"Gateway not ready after {waited}s")
    return {
        "ready": False,
        "message": f"Gateway failed to connect within {waited}s",
        "waited": waited,
        "status": await check_gateway_status()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
