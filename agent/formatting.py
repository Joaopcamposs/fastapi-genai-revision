from src.orm_models import Order, Product


def format_products(products: list[Product]) -> str:
    """Render a product list as plain text, for LLM/tool consumption."""
    if not products:
        return "No products found."
    return "\n".join(f"{product.name}: ${product.price:.2f}" for product in products)


def format_orders(orders: list[Order]) -> str:
    """Render an order list as plain text, for LLM/tool consumption."""
    if not orders:
        return "No orders found."
    lines = []
    for order in orders:
        total = sum(item.unit_price * item.quantity for item in order.items)
        lines.append(
            f"Order {order.id}: {len(order.items)} item(s), total ${total:.2f}"
        )
    return "\n".join(lines)
