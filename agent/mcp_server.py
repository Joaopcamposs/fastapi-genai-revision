"""MCP server exposing the project's product/order read tools.

Runs as a standalone stdio server (e.g. for Claude Desktop), separate from
the FastAPI app. Unlike `/agent/ask`, there is no JWT session here: MCP
clients invoke tools directly, so `list_orders` takes the user's email as
an explicit argument instead of relying on an authenticated request.
Products are public (no tenant scoping), same as in the HTTP API.
"""

import sys
from pathlib import Path

# `mcp dev`/`mcp run` load this file directly via importlib, without adding
# the project root to sys.path (unlike `python -m agent.mcp_server`). Add it
# here so `agent.*`/`src.*` imports work regardless of how this is launched.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.mcpserver import MCPServer

from agent.formatting import format_orders, format_products
from src.domain_repo import UserRepository
from src.view_repo import OrderViewRepo, ProductViewRepo

mcp = MCPServer("fastapi-genai-revision")


@mcp.tool()
async def list_products() -> str:
    """List available products (public), with name and price."""
    products = await ProductViewRepo().list()
    return format_products(products)


@mcp.tool()
async def list_orders(user_email: str) -> str:
    """List the orders belonging to the user with the given email."""
    user = await UserRepository().get_by_email(user_email)
    if not user:
        return f"No user found with email {user_email}."
    orders = await OrderViewRepo().list_by_user(user.id)
    return format_orders(orders)


if __name__ == "__main__":
    mcp.run()
