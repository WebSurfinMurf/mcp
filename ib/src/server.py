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
- Direct ib_async connection for options data (reqSecDefOptParams)
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
import ib_async as ib

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

# Options-specific configuration (longer timeouts for options data)
OPTIONS_TIMEOUT = int(os.getenv("OPTIONS_TIMEOUT", "120"))  # 2 minutes for options chains
OPTIONS_CLIENT_ID = int(os.getenv("OPTIONS_CLIENT_ID", "99"))  # Dedicated client ID for options

# Gateway control configuration
# Uses Docker to control the gateway container
GATEWAY_CONTAINER = os.getenv("GATEWAY_CONTAINER", "mcp-ib-gateway")
DOCKER_SOCKET = "/var/run/docker.sock"


# ============================================================================
# Direct ib_async Options Client
# Uses reqSecDefOptParams for proper options chain data (no throttling)
# ============================================================================

class OptionsClient:
    """
    Dedicated IB client for options data using ib_async directly.
    Uses reqSecDefOptParams which doesn't have the throttling limitations
    of reqContractDetails for options.
    """

    def __init__(self, host: str, port: int, client_id: int):
        self.host = host
        self.port = port
        self.client_id = client_id
        self._ib: Optional[ib.IB] = None
        self._lock = asyncio.Lock()
        self._connected = False

    async def connect(self) -> bool:
        """Connect to IB Gateway"""
        async with self._lock:
            if self._connected and self._ib and self._ib.isConnected():
                return True

            try:
                self._ib = ib.IB()
                await self._ib.connectAsync(
                    self.host,
                    self.port,
                    clientId=self.client_id,
                    readonly=True,
                    timeout=30
                )
                self._connected = True
                logger.info(f"Options client connected to IB at {self.host}:{self.port}")
                return True
            except Exception as e:
                logger.error(f"Options client failed to connect: {e}")
                self._connected = False
                return False

    async def disconnect(self):
        """Disconnect from IB Gateway"""
        async with self._lock:
            if self._ib:
                self._ib.disconnect()
                self._connected = False
                logger.info("Options client disconnected")

    async def ensure_connected(self) -> bool:
        """Ensure connection is active, reconnect if needed"""
        if not self._connected or not self._ib or not self._ib.isConnected():
            return await self.connect()
        return True

    async def get_stock_contract(self, symbol: str) -> Optional[ib.Stock]:
        """Get qualified stock contract"""
        if not await self.ensure_connected():
            return None

        try:
            stock = ib.Stock(symbol.upper(), "SMART", "USD")
            contracts = await asyncio.wait_for(
                self._ib.qualifyContractsAsync(stock),
                timeout=30
            )
            if contracts:
                return contracts[0] if isinstance(contracts[0], ib.Contract) else None
            return None
        except Exception as e:
            logger.error(f"Failed to get stock contract for {symbol}: {e}")
            return None

    async def get_stock_price(self, symbol: str) -> Optional[float]:
        """Get current stock price using market data snapshot"""
        if not await self.ensure_connected():
            return None

        try:
            stock = await self.get_stock_contract(symbol)
            if not stock:
                return None

            # Request market data type 4 = delayed frozen data (available without subscription)
            self._ib.reqMarketDataType(4)

            # Request ticker
            ticker = self._ib.reqMktData(stock, '', False, False)
            await asyncio.sleep(2)  # Wait for data

            # Cancel market data
            self._ib.cancelMktData(stock)

            # Get price (try last, then close, then bid/ask midpoint)
            price = ticker.last
            if not price or price <= 0:
                price = ticker.close
            if not price or price <= 0:
                if ticker.bid and ticker.ask and ticker.bid > 0 and ticker.ask > 0:
                    price = (ticker.bid + ticker.ask) / 2

            return float(price) if price and price > 0 else None
        except Exception as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
            return None

    async def get_option_expirations(self, symbol: str) -> List[str]:
        """
        Get available option expiration dates using reqSecDefOptParams.
        This is the proper way to get options data - no throttling.

        Returns list of expiration dates in YYYYMMDD format.
        """
        if not await self.ensure_connected():
            return []

        try:
            stock = await self.get_stock_contract(symbol)
            if not stock:
                logger.error(f"Could not qualify stock contract for {symbol}")
                return []

            logger.info(f"Requesting option params for {symbol} (conId={stock.conId})")

            # Use reqSecDefOptParams - this is the proper way to get options chain params
            # It returns expirations and strikes without throttling
            chains = await asyncio.wait_for(
                self._ib.reqSecDefOptParamsAsync(
                    underlyingSymbol=stock.symbol,
                    futFopExchange="",  # Empty for stocks
                    underlyingSecType=stock.secType,
                    underlyingConId=stock.conId
                ),
                timeout=OPTIONS_TIMEOUT
            )

            if not chains:
                logger.warning(f"No option chains returned for {symbol}")
                return []

            # Get the SMART exchange chain (most liquid)
            smart_chain = next((c for c in chains if c.exchange == "SMART"), None)
            if not smart_chain:
                # Fall back to first available
                smart_chain = chains[0]

            expirations = sorted(list(smart_chain.expirations))
            logger.info(f"Found {len(expirations)} expirations for {symbol}")
            return expirations

        except asyncio.TimeoutError:
            logger.error(f"Timeout getting option expirations for {symbol}")
            return []
        except Exception as e:
            logger.error(f"Failed to get option expirations for {symbol}: {e}")
            return []

    async def get_option_chain(
        self,
        symbol: str,
        expiration: str,
        strikes_range: int = 20
    ) -> Dict[str, Any]:
        """
        Get options chain with market data for a specific expiration.

        Args:
            symbol: Stock symbol
            expiration: Expiration date in YYYYMMDD format
            strikes_range: Number of strikes on each side of ATM

        Returns dict with underlying_price, calls, puts
        """
        if not await self.ensure_connected():
            return {"error": "Not connected to IB"}

        try:
            stock = await self.get_stock_contract(symbol)
            if not stock:
                return {"error": f"Could not qualify stock contract for {symbol}"}

            # Get current price
            underlying_price = await self.get_stock_price(symbol)
            if not underlying_price:
                logger.warning(f"Could not get underlying price for {symbol}, using last close")

            # Get option chain parameters
            chains = await asyncio.wait_for(
                self._ib.reqSecDefOptParamsAsync(
                    underlyingSymbol=stock.symbol,
                    futFopExchange="",
                    underlyingSecType=stock.secType,
                    underlyingConId=stock.conId
                ),
                timeout=OPTIONS_TIMEOUT
            )

            if not chains:
                return {"error": f"No option chains found for {symbol}"}

            # Get SMART exchange chain
            chain = next((c for c in chains if c.exchange == "SMART"), chains[0])

            # Verify expiration exists
            if expiration not in chain.expirations:
                return {"error": f"Expiration {expiration} not found for {symbol}"}

            # Filter strikes around ATM
            all_strikes = sorted(chain.strikes)
            if underlying_price:
                # Find ATM strike
                atm_idx = min(range(len(all_strikes)),
                             key=lambda i: abs(all_strikes[i] - underlying_price))
                start_idx = max(0, atm_idx - strikes_range)
                end_idx = min(len(all_strikes), atm_idx + strikes_range + 1)
                strikes = all_strikes[start_idx:end_idx]
            else:
                # Take middle strikes if no price
                mid = len(all_strikes) // 2
                strikes = all_strikes[max(0, mid-strikes_range):mid+strikes_range+1]

            logger.info(f"Getting {len(strikes)} strikes for {symbol} {expiration}")

            # Create option contracts
            calls = []
            puts = []

            # Request market data type 4 = delayed frozen data
            self._ib.reqMarketDataType(4)

            # Build call and put contracts
            call_contracts = [
                ib.Option(symbol, expiration, strike, "C", "SMART", tradingClass=chain.tradingClass)
                for strike in strikes
            ]
            put_contracts = [
                ib.Option(symbol, expiration, strike, "P", "SMART", tradingClass=chain.tradingClass)
                for strike in strikes
            ]

            # Qualify contracts in batches to avoid pacing violations
            all_contracts = call_contracts + put_contracts
            qualified = []
            batch_size = 50

            for i in range(0, len(all_contracts), batch_size):
                batch = all_contracts[i:i+batch_size]
                try:
                    batch_qualified = await asyncio.wait_for(
                        self._ib.qualifyContractsAsync(*batch),
                        timeout=30
                    )
                    qualified.extend([c for c in batch_qualified if c])
                    await asyncio.sleep(0.5)  # Respect pacing
                except Exception as e:
                    logger.warning(f"Batch qualification failed: {e}")

            if not qualified:
                return {
                    "symbol": symbol,
                    "expiration": expiration,
                    "underlying_price": underlying_price,
                    "calls": [],
                    "puts": [],
                    "note": "No contracts qualified - may need market data subscription"
                }

            # Request tickers for all qualified contracts
            tickers = []
            for contract in qualified:
                try:
                    ticker = self._ib.reqMktData(contract, '', False, False)
                    tickers.append((contract, ticker))
                except Exception as e:
                    logger.debug(f"Failed to request ticker for {contract}: {e}")

            # Wait for data
            await asyncio.sleep(3)

            # Process tickers
            for contract, ticker in tickers:
                contract_data = {
                    "strike": contract.strike,
                    "bid": ticker.bid if ticker.bid and ticker.bid > 0 else None,
                    "ask": ticker.ask if ticker.ask and ticker.ask > 0 else None,
                    "last": ticker.last if ticker.last and ticker.last > 0 else None,
                    "volume": ticker.volume if ticker.volume else None,
                    "open_interest": None,  # Requires separate request
                    "iv": None,  # Will be calculated
                    "greeks": None
                }

                # Add Greeks if available
                if ticker.modelGreeks:
                    contract_data["greeks"] = {
                        "delta": ticker.modelGreeks.delta,
                        "gamma": ticker.modelGreeks.gamma,
                        "theta": ticker.modelGreeks.theta,
                        "vega": ticker.modelGreeks.vega,
                        "iv": ticker.modelGreeks.impliedVol
                    }
                    contract_data["iv"] = ticker.modelGreeks.impliedVol

                if contract.right == "C":
                    calls.append(contract_data)
                else:
                    puts.append(contract_data)

                # Cancel market data
                self._ib.cancelMktData(contract)

            # Sort by strike
            calls.sort(key=lambda x: x["strike"])
            puts.sort(key=lambda x: x["strike"])

            return {
                "symbol": symbol,
                "expiration": expiration,
                "underlying_price": underlying_price,
                "calls": calls,
                "puts": puts,
                "trading_class": chain.tradingClass,
                "multiplier": chain.multiplier
            }

        except asyncio.TimeoutError:
            return {"error": f"Timeout getting option chain for {symbol}"}
        except Exception as e:
            logger.error(f"Failed to get option chain for {symbol}: {e}")
            return {"error": str(e)}


# Global options client instance
options_client: Optional[OptionsClient] = None


# ============================================================================
# Orders Client for Paper Trading
# Uses ib_async directly for order placement
# ============================================================================

class OrdersClient:
    """
    Dedicated IB client for order placement using ib_async directly.
    Requires IB_READONLY=false in environment.
    """

    def __init__(self, host: str, port: int, client_id: int):
        self.host = host
        self.port = port
        self.client_id = client_id
        self._ib: Optional[ib.IB] = None
        self._lock = asyncio.Lock()
        self._connected = False
        self._readonly = os.getenv("IB_READONLY", "true").lower() == "true"

    async def connect(self) -> bool:
        """Connect to IB Gateway"""
        async with self._lock:
            if self._connected and self._ib and self._ib.isConnected():
                return True

            try:
                self._ib = ib.IB()
                await self._ib.connectAsync(
                    self.host,
                    self.port,
                    clientId=self.client_id,
                    readonly=self._readonly,  # Use config setting
                    timeout=30
                )
                self._connected = True
                logger.info(f"Orders client connected to IB at {self.host}:{self.port} (readonly={self._readonly})")
                return True
            except Exception as e:
                logger.error(f"Orders client failed to connect: {e}")
                self._connected = False
                return False

    async def disconnect(self):
        """Disconnect from IB Gateway"""
        async with self._lock:
            if self._ib:
                self._ib.disconnect()
                self._connected = False
                logger.info("Orders client disconnected")

    async def ensure_connected(self) -> bool:
        """Ensure connection is active, reconnect if needed"""
        if not self._connected or not self._ib or not self._ib.isConnected():
            return await self.connect()
        return True

    async def get_option_contract(
        self,
        symbol: str,
        expiration: str,
        strike: float,
        right: str
    ) -> Optional[ib.Option]:
        """
        Get qualified option contract.

        Args:
            symbol: Underlying symbol (e.g., AAPL)
            expiration: Expiration in YYYYMMDD format
            strike: Strike price
            right: 'C' for call, 'P' for put
        """
        if not await self.ensure_connected():
            return None

        try:
            option = ib.Option(
                symbol.upper(),
                expiration,
                strike,
                right.upper(),
                "SMART"
            )
            contracts = await asyncio.wait_for(
                self._ib.qualifyContractsAsync(option),
                timeout=30
            )
            if contracts and len(contracts) > 0:
                return contracts[0]
            return None
        except Exception as e:
            logger.error(f"Failed to qualify option contract: {e}")
            return None

    async def place_option_order(
        self,
        symbol: str,
        expiration: str,
        strike: float,
        right: str,
        action: str,
        quantity: int,
        order_type: str = "LMT",
        limit_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Place an option order.

        Args:
            symbol: Underlying symbol
            expiration: Expiration in YYYYMMDD format
            strike: Strike price
            right: 'C' for call, 'P' for put
            action: 'BUY' or 'SELL'
            quantity: Number of contracts
            order_type: 'LMT' or 'MKT'
            limit_price: Required for limit orders

        Returns:
            Dict with order_id, status, and details
        """
        if self._readonly:
            return {
                "success": False,
                "error": "Order placement disabled (IB_READONLY=true)",
                "note": "Set IB_READONLY=false in mcp-ib.env to enable trading"
            }

        if not await self.ensure_connected():
            return {
                "success": False,
                "error": "Not connected to IB Gateway"
            }

        try:
            # Get qualified contract
            contract = await self.get_option_contract(symbol, expiration, strike, right)
            if not contract:
                return {
                    "success": False,
                    "error": f"Could not find option contract: {symbol} {expiration} {strike} {right}"
                }

            # Create order
            if order_type.upper() == "MKT":
                order = ib.MarketOrder(action.upper(), quantity)
            else:
                if limit_price is None:
                    return {
                        "success": False,
                        "error": "Limit price required for limit orders"
                    }
                order = ib.LimitOrder(action.upper(), quantity, limit_price)

            # Place the order
            trade = self._ib.placeOrder(contract, order)

            # Wait for order acknowledgment
            await asyncio.sleep(1)

            return {
                "success": True,
                "order_id": trade.order.orderId,
                "perm_id": trade.order.permId,
                "status": trade.orderStatus.status,
                "filled": trade.orderStatus.filled,
                "remaining": trade.orderStatus.remaining,
                "avg_fill_price": trade.orderStatus.avgFillPrice,
                "contract": {
                    "symbol": contract.symbol,
                    "expiration": contract.lastTradeDateOrContractMonth,
                    "strike": contract.strike,
                    "right": contract.right,
                    "exchange": contract.exchange
                },
                "order": {
                    "action": order.action,
                    "quantity": order.totalQuantity,
                    "type": order.orderType,
                    "limit_price": getattr(order, 'lmtPrice', None)
                }
            }

        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def place_combo_order(
        self,
        legs: List[Dict[str, Any]],
        action: str,
        quantity: int,
        order_type: str = "LMT",
        limit_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Place a multi-leg combo order (spread).

        Args:
            legs: List of leg definitions, each with:
                - symbol: Underlying symbol
                - expiration: YYYYMMDD format
                - strike: Strike price
                - right: 'C' or 'P'
                - action: 'BUY' or 'SELL' for this leg
                - ratio: Usually 1
            action: Overall combo action (BUY = enter, SELL = exit)
            quantity: Number of combo contracts
            order_type: 'LMT' or 'MKT'
            limit_price: Net debit (positive) or credit (negative) for the combo

        Returns:
            Dict with order details
        """
        if self._readonly:
            return {
                "success": False,
                "error": "Order placement disabled (IB_READONLY=true)",
                "note": "Set IB_READONLY=false in mcp-ib.env to enable trading"
            }

        if not await self.ensure_connected():
            return {
                "success": False,
                "error": "Not connected to IB Gateway"
            }

        try:
            # Qualify all leg contracts
            combo_legs = []
            for leg in legs:
                contract = await self.get_option_contract(
                    leg["symbol"],
                    leg["expiration"],
                    leg["strike"],
                    leg["right"]
                )
                if not contract:
                    return {
                        "success": False,
                        "error": f"Could not find contract for leg: {leg}"
                    }

                combo_leg = ib.ComboLeg(
                    conId=contract.conId,
                    ratio=leg.get("ratio", 1),
                    action=leg["action"].upper(),
                    exchange="SMART"
                )
                combo_legs.append(combo_leg)

            # Create combo contract
            combo = ib.Contract()
            combo.symbol = legs[0]["symbol"]
            combo.secType = "BAG"
            combo.currency = "USD"
            combo.exchange = "SMART"
            combo.comboLegs = combo_legs

            # Create order
            if order_type.upper() == "MKT":
                order = ib.MarketOrder(action.upper(), quantity)
            else:
                if limit_price is None:
                    return {
                        "success": False,
                        "error": "Limit price required for limit orders"
                    }
                order = ib.LimitOrder(action.upper(), quantity, limit_price)

            # Place the order
            trade = self._ib.placeOrder(combo, order)

            # Wait for order acknowledgment
            await asyncio.sleep(1)

            return {
                "success": True,
                "order_id": trade.order.orderId,
                "perm_id": trade.order.permId,
                "status": trade.orderStatus.status,
                "filled": trade.orderStatus.filled,
                "remaining": trade.orderStatus.remaining,
                "avg_fill_price": trade.orderStatus.avgFillPrice,
                "combo_legs": [
                    {
                        "conId": cl.conId,
                        "action": cl.action,
                        "ratio": cl.ratio
                    }
                    for cl in combo_legs
                ],
                "order": {
                    "action": order.action,
                    "quantity": order.totalQuantity,
                    "type": order.orderType,
                    "limit_price": getattr(order, 'lmtPrice', None)
                }
            }

        except Exception as e:
            logger.error(f"Failed to place combo order: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_order_status(self, order_id: int) -> Dict[str, Any]:
        """Get status of a specific order"""
        if not await self.ensure_connected():
            return {"error": "Not connected to IB Gateway"}

        try:
            # Get all open orders
            trades = self._ib.trades()

            for trade in trades:
                if trade.order.orderId == order_id:
                    return {
                        "found": True,
                        "order_id": trade.order.orderId,
                        "status": trade.orderStatus.status,
                        "filled": trade.orderStatus.filled,
                        "remaining": trade.orderStatus.remaining,
                        "avg_fill_price": trade.orderStatus.avgFillPrice,
                        "last_fill_price": trade.orderStatus.lastFillPrice,
                        "why_held": trade.orderStatus.whyHeld
                    }

            return {
                "found": False,
                "order_id": order_id,
                "note": "Order not found in open orders"
            }

        except Exception as e:
            logger.error(f"Failed to get order status: {e}")
            return {"error": str(e)}

    async def cancel_order(self, order_id: int) -> Dict[str, Any]:
        """Cancel an open order"""
        if self._readonly:
            return {
                "success": False,
                "error": "Order cancellation disabled (IB_READONLY=true)"
            }

        if not await self.ensure_connected():
            return {"error": "Not connected to IB Gateway"}

        try:
            trades = self._ib.trades()

            for trade in trades:
                if trade.order.orderId == order_id:
                    self._ib.cancelOrder(trade.order)
                    await asyncio.sleep(0.5)

                    return {
                        "success": True,
                        "order_id": order_id,
                        "status": "Cancel requested"
                    }

            return {
                "success": False,
                "error": f"Order {order_id} not found"
            }

        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            return {"success": False, "error": str(e)}

    async def get_open_orders(self) -> List[Dict[str, Any]]:
        """Get all open orders"""
        if not await self.ensure_connected():
            return []

        try:
            trades = self._ib.trades()
            orders = []

            for trade in trades:
                orders.append({
                    "order_id": trade.order.orderId,
                    "perm_id": trade.order.permId,
                    "status": trade.orderStatus.status,
                    "action": trade.order.action,
                    "quantity": trade.order.totalQuantity,
                    "filled": trade.orderStatus.filled,
                    "remaining": trade.orderStatus.remaining,
                    "order_type": trade.order.orderType,
                    "limit_price": getattr(trade.order, 'lmtPrice', None),
                    "avg_fill_price": trade.orderStatus.avgFillPrice
                })

            return orders

        except Exception as e:
            logger.error(f"Failed to get open orders: {e}")
            return []


# Global orders client instance
orders_client: Optional[OrdersClient] = None

# Client ID for orders (separate from options to avoid conflicts)
ORDERS_CLIENT_ID = int(os.getenv("ORDERS_CLIENT_ID", "98"))


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

                # Auto-reconnect gateway only if BOTH workers AND options_client are disconnected
                # This prevents unnecessary gateway restarts when options_client is working fine
                options_client_ok = (
                    options_client is not None and
                    options_client._connected and
                    options_client._ib is not None and
                    options_client._ib.isConnected()
                )

                if workers_connected == 0 and not options_client_ok:
                    consecutive_disconnects += 1
                    logger.warning(f"All IB connections lost ({consecutive_disconnects} consecutive checks)")

                    if consecutive_disconnects >= 2:
                        logger.info("Auto-reconnecting gateway after sustained disconnection...")
                        await self._auto_reconnect_gateway()
                        consecutive_disconnects = 0
                        # Reset all worker restart counts after gateway reconnect
                        for worker in self.workers:
                            worker.restart_count = 0
                            worker.consecutive_failures = 0
                        # Try to reconnect options_client
                        if options_client:
                            try:
                                await options_client.connect()
                            except Exception as e:
                                logger.warning(f"Options client reconnect failed: {e}")
                elif workers_connected > 0 or options_client_ok:
                    # At least one connection type is working, reset counter
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
    global pool, options_client, orders_client
    logger.info(f"Starting MCP IB Server with {POOL_SIZE} workers")
    logger.info(f"Connecting to {IB_HOST}:{IB_PORT}, base client_id={IB_CLIENT_ID_BASE}")
    logger.info(f"Health check interval: {HEALTH_CHECK_INTERVAL}s, Max retries: {MAX_RETRIES}")
    logger.info(f"Options timeout: {OPTIONS_TIMEOUT}s, Options client_id: {OPTIONS_CLIENT_ID}")
    logger.info(f"Orders client_id: {ORDERS_CLIENT_ID}, IB_READONLY={os.getenv('IB_READONLY', 'true')}")

    # Initialize MCP worker pool
    pool = IBWorkerPool(size=POOL_SIZE, base_client_id=IB_CLIENT_ID_BASE)
    await pool.initialize()
    await pool.start_health_monitor()

    # Initialize dedicated options client (uses ib_async directly for reqSecDefOptParams)
    options_client = OptionsClient(
        host=IB_HOST,
        port=int(IB_PORT),
        client_id=OPTIONS_CLIENT_ID
    )
    # Try to connect but don't fail startup if it fails
    try:
        await options_client.connect()
    except Exception as e:
        logger.warning(f"Options client failed to connect on startup: {e}")

    # Initialize orders client for paper trading
    orders_client = OrdersClient(
        host=IB_HOST,
        port=int(IB_PORT),
        client_id=ORDERS_CLIENT_ID
    )
    # Try to connect but don't fail startup if it fails
    try:
        await orders_client.connect()
    except Exception as e:
        logger.warning(f"Orders client failed to connect on startup: {e}")

    yield

    logger.info("Shutting down MCP IB Server")
    if orders_client:
        await orders_client.disconnect()
    if options_client:
        await options_client.disconnect()
    await pool.shutdown()


app = FastAPI(title="MCP IB Server", version="2.1.0", lifespan=lifespan)


@app.get("/health")
async def health_check():
    """Health check endpoint with real IB connectivity status"""
    pool_stats = pool.get_stats() if pool else None

    # Check options client connection (primary connection for options data)
    options_connected = False
    if options_client:
        options_connected = options_client._connected and options_client._ib and options_client._ib.isConnected()

    # Determine overall status - options_client is now the primary IB connection
    # Workers are only used for MCP protocol calls (get_account_summary, etc.)
    if pool_stats:
        workers_ib_connected = pool_stats["workers_ib_connected"] > 0
        workers_alive = pool_stats["workers_alive"] > 0
    else:
        workers_ib_connected = False
        workers_alive = False

    # IB is connected if EITHER options_client OR workers are connected
    ib_connected = options_connected or workers_ib_connected

    cb_status = circuit_breaker.get_status()

    if cb_status["state"] == "open":
        status = "unhealthy"
    elif not ib_connected:
        status = "unhealthy"
    elif not options_connected:
        # Workers connected but options client not - degraded for options
        status = "degraded"
    else:
        status = "healthy"

    return {
        "status": status,
        "ib_connected": ib_connected,
        "options_client_connected": options_connected,
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


# ============================================================================
# Options Data REST Endpoints (for optionsearch integration)
# Uses dedicated OptionsClient with ib_async for reqSecDefOptParams
# ============================================================================

@app.get("/options/expirations/{symbol}")
async def get_option_expirations(symbol: str):
    """
    Get available option expiration dates for a symbol.

    Uses reqSecDefOptParams for proper options data retrieval (no throttling).
    Returns list of expiration dates in YYYYMMDD format.
    """
    global options_client

    if not options_client:
        return {"error": "Options client not initialized", "symbol": symbol}

    try:
        expirations = await options_client.get_option_expirations(symbol.upper())

        if not expirations:
            return {
                "error": "No expirations found - check market data subscription",
                "symbol": symbol,
                "expirations": []
            }

        return {
            "symbol": symbol.upper(),
            "expirations": expirations,
            "count": len(expirations)
        }
    except Exception as e:
        logger.error(f"Error getting expirations for {symbol}: {e}")
        return {"error": str(e), "symbol": symbol}


@app.get("/options/chain/{symbol}/{expiration}")
async def get_option_chain(symbol: str, expiration: str, strikes: int = 20):
    """
    Get options chain for a symbol and expiration.

    Uses reqSecDefOptParams and market data requests.

    Args:
        symbol: Stock symbol (e.g., AAPL)
        expiration: Expiration date in YYYYMMDD format
        strikes: Number of strikes on each side of ATM (default 20)

    Returns calls and puts with bid/ask/last/greeks.
    """
    global options_client

    if not options_client:
        return {"error": "Options client not initialized", "symbol": symbol}

    try:
        result = await options_client.get_option_chain(
            symbol=symbol.upper(),
            expiration=expiration,
            strikes_range=strikes
        )

        if "error" in result:
            return result

        return result
    except Exception as e:
        logger.error(f"Error getting chain for {symbol} {expiration}: {e}")
        return {"error": str(e), "symbol": symbol, "expiration": expiration}


@app.get("/options/quote/{symbol}")
async def get_stock_quote(symbol: str):
    """
    Get current stock quote with price.

    Uses options client for market data if available, falls back to historical data.
    Returns price, bid, ask, volume.
    """
    global options_client

    # Try using options client first (uses live market data)
    if options_client:
        try:
            if await options_client.ensure_connected():
                stock = await options_client.get_stock_contract(symbol.upper())
                if stock:
                    # Request market data type 4 = delayed frozen data
                    options_client._ib.reqMarketDataType(4)

                    ticker = options_client._ib.reqMktData(stock, '', False, False)
                    await asyncio.sleep(2)

                    options_client._ib.cancelMktData(stock)

                    price = ticker.last
                    if not price or price <= 0:
                        price = ticker.close
                    if not price or price <= 0:
                        if ticker.bid and ticker.ask and ticker.bid > 0 and ticker.ask > 0:
                            price = (ticker.bid + ticker.ask) / 2

                    if price and price > 0:
                        return {
                            "symbol": symbol.upper(),
                            "price": float(price),
                            "bid": float(ticker.bid) if ticker.bid and ticker.bid > 0 else None,
                            "ask": float(ticker.ask) if ticker.ask and ticker.ask > 0 else None,
                            "last": float(ticker.last) if ticker.last and ticker.last > 0 else None,
                            "volume": int(ticker.volume) if ticker.volume else None,
                            "source": "market_data"
                        }
        except Exception as e:
            logger.warning(f"Options client quote failed for {symbol}, falling back to historical: {e}")

    # Fall back to historical data via MCP
    request = {
        "jsonrpc": "2.0",
        "id": "quote-1",
        "method": "tools/call",
        "params": {
            "name": "get_historical_data",
            "arguments": {
                "symbol": symbol.upper(),
                "duration": "1 D",
                "bar_size": "1 min"
            }
        }
    }

    result = await send_to_ib_mcp(request)

    if "error" in result:
        return {"error": result["error"], "symbol": symbol}

    try:
        content = result.get("result", {}).get("content", [])
        if content and len(content) > 0:
            text = content[0].get("text", "")
            # Parse the markdown table format
            # Format: | Date | Open | High | Low | Close | Volume |
            lines = text.strip().split('\n')

            # Find data lines (those starting with | and containing numbers)
            data_lines = []
            for line in lines:
                if line.startswith('|') and 'Date' not in line and '---' not in line and '*' not in line:
                    data_lines.append(line)

            if data_lines:
                # Get the last data line (most recent)
                last_line = data_lines[-1]
                # Split by | and strip whitespace
                parts = [p.strip() for p in last_line.split('|') if p.strip()]
                # parts: [Date, Open, High, Low, Close, Volume]
                if len(parts) >= 6:
                    return {
                        "symbol": symbol.upper(),
                        "price": float(parts[4]) if parts[4] else None,  # Close
                        "open": float(parts[1]) if parts[1] else None,
                        "high": float(parts[2]) if parts[2] else None,
                        "low": float(parts[3]) if parts[3] else None,
                        "volume": int(float(parts[5])) if parts[5] else None,
                        "timestamp": parts[0] if parts[0] else None,
                        "source": "historical"
                    }
    except Exception as e:
        return {"error": str(e), "symbol": symbol, "raw": result}

    return {"symbol": symbol, "price": None, "raw": result}


# ============================================================================
# Orders REST Endpoints (for paper trading)
# Requires IB_READONLY=false in environment
# ============================================================================

class SingleLegOrderRequest(BaseModel):
    """Request to place a single leg option order"""
    symbol: str
    expiration: str  # YYYYMMDD format
    strike: float
    right: str  # C or P
    action: str  # BUY or SELL
    quantity: int
    order_type: str = "LMT"  # LMT or MKT
    limit_price: Optional[float] = None


class ComboLeg(BaseModel):
    """Single leg in a combo order"""
    symbol: str
    expiration: str  # YYYYMMDD format
    strike: float
    right: str  # C or P
    action: str  # BUY or SELL
    ratio: int = 1


class ComboOrderRequest(BaseModel):
    """Request to place a multi-leg combo order (spread)"""
    legs: List[ComboLeg]
    action: str = "BUY"  # Overall combo action
    quantity: int
    order_type: str = "LMT"
    limit_price: Optional[float] = None


@app.get("/orders/capability")
async def get_order_capability():
    """
    Check if order placement is enabled.

    Returns readonly status and connection state.
    """
    global orders_client

    readonly = os.getenv("IB_READONLY", "true").lower() == "true"
    connected = False

    if orders_client:
        connected = orders_client._connected and orders_client._ib and orders_client._ib.isConnected()

    return {
        "readonly": readonly,
        "connected": connected,
        "can_place_orders": not readonly and connected,
        "note": "Set IB_READONLY=false in mcp-ib.env to enable trading" if readonly else "Order placement enabled"
    }


@app.get("/orders")
async def get_open_orders():
    """
    Get all open orders.

    Returns list of orders with status, fills, etc.
    """
    global orders_client

    if not orders_client:
        return {"error": "Orders client not initialized"}

    try:
        orders = await orders_client.get_open_orders()
        return {
            "orders": orders,
            "count": len(orders),
            "readonly": orders_client._readonly
        }
    except Exception as e:
        logger.error(f"Error getting open orders: {e}")
        return {"error": str(e)}


@app.get("/orders/{order_id}")
async def get_order_status(order_id: int):
    """
    Get status of a specific order.

    Args:
        order_id: The IB order ID
    """
    global orders_client

    if not orders_client:
        return {"error": "Orders client not initialized"}

    return await orders_client.get_order_status(order_id)


@app.post("/orders/single")
async def place_single_order(request: SingleLegOrderRequest):
    """
    Place a single leg option order.

    This is for buying or selling individual options (calls or puts).
    """
    global orders_client

    if not orders_client:
        return {"error": "Orders client not initialized"}

    return await orders_client.place_option_order(
        symbol=request.symbol,
        expiration=request.expiration,
        strike=request.strike,
        right=request.right,
        action=request.action,
        quantity=request.quantity,
        order_type=request.order_type,
        limit_price=request.limit_price
    )


@app.post("/orders/combo")
async def place_combo_order(request: ComboOrderRequest):
    """
    Place a multi-leg combo order (spread).

    Use this for vertical spreads, iron condors, etc.
    The limit_price is the net premium:
    - Positive = net debit (you pay)
    - Negative = net credit (you receive)
    """
    global orders_client

    if not orders_client:
        return {"error": "Orders client not initialized"}

    legs = [leg.dict() for leg in request.legs]

    return await orders_client.place_combo_order(
        legs=legs,
        action=request.action,
        quantity=request.quantity,
        order_type=request.order_type,
        limit_price=request.limit_price
    )


@app.delete("/orders/{order_id}")
async def cancel_order(order_id: int):
    """
    Cancel an open order.

    Args:
        order_id: The IB order ID to cancel
    """
    global orders_client

    if not orders_client:
        return {"error": "Orders client not initialized"}

    return await orders_client.cancel_order(order_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
