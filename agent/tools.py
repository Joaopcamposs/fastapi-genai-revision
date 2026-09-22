from uuid import UUID

from langchain_core.tools import tool

from agent.formatting import format_orders, format_products
from src.view_repo import OrderViewRepo, ProductViewRepo


def build_tools(user_id: UUID) -> list:
    """Build the agent's tools, with orders scoped to the authenticated user."""

    @tool
    async def list_products() -> str:
        """List available products, with name and price."""
        products = await ProductViewRepo().list()
        return format_products(products)

    @tool
    async def list_orders() -> str:
        """List the authenticated user's orders, with items and total."""
        orders = await OrderViewRepo().list_by_user(user_id)
        return format_orders(orders)

    return [list_products, list_orders]
