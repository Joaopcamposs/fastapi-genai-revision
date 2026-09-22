from httpx import AsyncClient

from agent.mcp_server import list_orders, list_products


async def test_list_products_tool(client: AsyncClient, auth_headers: dict) -> None:
    await client.post(
        "/products/", json={"name": "Keyboard", "price": 250.0}, headers=auth_headers
    )

    result = await list_products()
    assert "Keyboard" in result
    assert "250.00" in result


async def test_list_products_tool_empty() -> None:
    result = await list_products()
    assert result == "No products found."


async def test_list_orders_tool_scoped_to_user(
    client: AsyncClient, auth_headers: dict
) -> None:
    product = await client.post(
        "/products/", json={"name": "Mouse", "price": 80.0}, headers=auth_headers
    )
    product_id = product.json()["id"]
    await client.post(
        "/orders/",
        json={"items": [{"product_id": product_id, "quantity": 2}]},
        headers=auth_headers,
    )

    result = await list_orders(user_email="user@example.com")
    assert "160.00" in result


async def test_list_orders_tool_unknown_user() -> None:
    result = await list_orders(user_email="nobody@example.com")
    assert "No user found" in result
