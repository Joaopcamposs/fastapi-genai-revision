from uuid import UUID

from httpx import AsyncClient

from agent.tools import build_tools


async def test_list_products_tool(client: AsyncClient, auth_headers: dict) -> None:
    await client.post(
        "/products/", json={"name": "Keyboard", "price": 250.0}, headers=auth_headers
    )
    me = await client.get("/users/user@example.com", headers=auth_headers)
    user_id = UUID(me.json()["id"])

    list_products, _ = build_tools(user_id)
    result = await list_products.ainvoke({})
    assert "Keyboard" in result
    assert "250.00" in result


async def test_list_products_tool_empty() -> None:
    list_products, _ = build_tools(UUID(int=0))
    result = await list_products.ainvoke({})
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

    me = await client.get("/users/user@example.com", headers=auth_headers)
    user_id = UUID(me.json()["id"])

    _, list_orders = build_tools(user_id)
    result = await list_orders.ainvoke({})
    assert "160.00" in result

    _, list_orders_other = build_tools(UUID(int=0))
    result_other = await list_orders_other.ainvoke({})
    assert result_other == "No orders found."
