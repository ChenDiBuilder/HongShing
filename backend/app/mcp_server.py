"""The restaurant's MCP server — the surface a Vela agent consumes.

Act 2 of the pilot architecture: the restaurant is the tool provider. An agent
that wants to sell this restaurant's food calls THESE tools, so every order an
agent takes lands in the restaurant's own database because the restaurant
executed it. No dispatch layer, no mirroring.

Transport: MCP streamable HTTP (stateless, JSON responses), mounted at /mcp on
the same FastAPI app — one box per restaurant, one service. Auth is a static
bearer service token (`MCP_SERVICE_TOKEN`); when the token is unset the mount
answers 404 and the feature simply does not exist. DNS-rebinding protection is
disabled because the bearer token is the gate and the box sits behind nginx
with its own Host handling.
"""
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from app.config import get_settings
from app.database import async_session
from app.services import agent_orders

settings = get_settings()

server = FastMCP(
    name="restaurant-ordering",
    instructions=(
        "Ordering and customer tools for this restaurant. Always identify the "
        "customer (name + phone) before placing an order — place_order will "
        "refuse otherwise. Prices come from get_menu; never invent prices. "
        "Read tool errors aloud to the customer in plain words."
    ),
    # Served at the mount root so the external path is exactly /mcp.
    streamable_http_path="/",
    stateless_http=True,
    json_response=True,
)


@server.tool()
async def get_menu() -> dict:
    """The current menu: categories, dish names, descriptions and prices in cents.

    Only available dishes are listed. Use the exact dish names from here when
    calling place_order."""
    async with async_session() as db:
        return await agent_orders.menu_snapshot(db)


@server.tool()
async def lookup_customer(phone: str) -> dict:
    """What the restaurant knows about a phone number: name, visit count, their
    usual dishes, and any live reward codes. A stranger returns found=false —
    that is normal, take the order and identity as usual."""
    async with async_session() as db:
        return await agent_orders.customer_context(db, phone)


@server.tool()
async def place_order(
    phone: str,
    name: str,
    items: list[dict],
    reward_code: str | None = None,
) -> dict:
    """Place a pickup order. REQUIRES the customer's name and phone number.

    items is a list of {"name": "<exact dish name from get_menu>", "quantity": n}.
    Optionally pass one of the customer's live reward codes to apply the
    discount. Returns the order id, an itemised total, and the applied reward.
    On ok=false, read the error to the customer and correct the order."""
    async with async_session() as db:
        return await agent_orders.create_agent_order(db, phone, name, items, reward_code)


@server.tool()
async def get_order_status(order_id: str) -> dict:
    """Status of a previously placed order (confirmed / preparing / ready)."""
    async with async_session() as db:
        return await agent_orders.order_status(db, order_id)


class TokenGate:
    """Minimal ASGI wrapper: bearer-token check in front of the MCP mount.

    404 when the feature is off (no token configured) so the path does not
    advertise itself; 401 on a missing/wrong token.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        token = get_settings().mcp_service_token
        status = None
        if not token:
            status = 404
        else:
            headers = dict(scope.get("headers") or [])
            auth = headers.get(b"authorization", b"").decode()
            if auth != f"Bearer {token}":
                status = 401
        if status is not None:
            await send(
                {
                    "type": "http.response.start",
                    "status": status,
                    "headers": [(b"content-type", b"text/plain")],
                }
            )
            await send({"type": "http.response.body", "body": b""})
            return
        await self.app(scope, receive, send)


def build_mcp_asgi():
    """The mountable ASGI app (path comes from the server settings above)."""
    return TokenGate(server.streamable_http_app())


@asynccontextmanager
async def mcp_lifespan():
    """Run the MCP session manager for the app's lifetime.

    Starlette does not run a mounted sub-app's lifespan, so the parent app's
    lifespan must enter this — without it every MCP request 500s."""
    async with server.session_manager.run():
        yield
