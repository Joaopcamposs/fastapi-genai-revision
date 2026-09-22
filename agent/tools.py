from uuid import UUID

from langchain_core.tools import tool

from src.view_repo import OrderViewRepo, ProductViewRepo


def build_tools(user_id: UUID) -> list:
    """Build the agent's tools, with orders scoped to the authenticated user."""

    @tool
    async def list_products() -> str:
        """List available products, with name and price."""
        products = await ProductViewRepo().list()
        if not products:
            return "No products found."
        return "\n".join(
            f"{product.name}: ${product.price:.2f}" for product in products
        )

    @tool
    async def list_orders() -> str:
        """List the authenticated user's orders, with items and total."""
        orders = await OrderViewRepo().list_by_user(user_id)
        if not orders:
            return "No orders found."
        lines = []
        for order in orders:
            total = sum(item.unit_price * item.quantity for item in order.items)
            lines.append(
                f"Order {order.id}: {len(order.items)} item(s), total ${total:.2f}"
            )
        return "\n".join(lines)

    return [list_products, list_orders]
