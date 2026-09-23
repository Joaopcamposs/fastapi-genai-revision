from httpx import AsyncClient


async def test_create_product_requires_auth(client: AsyncClient) -> None:
    response = await client.post(
        "/products/", json={"name": "Keyboard", "price": 250.0}
    )
    assert response.status_code == 401


async def test_create_product(client: AsyncClient, auth_headers: dict) -> None:
    response = await client.post(
        "/products/", json={"name": "Keyboard", "price": 250.0}, headers=auth_headers
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Keyboard"
    assert body["price"] == 250.0
    assert "id" in body


async def test_create_product_negative_price_fails(
    client: AsyncClient, auth_headers: dict
) -> None:
    response = await client.post(
        "/products/", json={"name": "Broken", "price": -10.0}, headers=auth_headers
    )
    assert response.status_code == 400


async def test_list_products_no_auth_required(client: AsyncClient) -> None:
    response = await client.get("/products/")
    assert response.status_code == 200


async def test_list_products(client: AsyncClient, auth_headers: dict) -> None:
    await client.post(
        "/products/", json={"name": "Mouse", "price": 80.0}, headers=auth_headers
    )
    response = await client.get("/products/", headers=auth_headers)
    assert response.status_code == 200
    names = [product["name"] for product in response.json()]
    assert "Mouse" in names


async def test_list_products_visible_across_users(
    client: AsyncClient, auth_headers: dict
) -> None:
    """Products are public: any authenticated user sees products others created."""
    await client.post(
        "/products/", json={"name": "Mouse", "price": 80.0}, headers=auth_headers
    )

    await client.post(
        "/users/", json={"email": "other@example.com", "password": "secret123"}
    )
    other_login = await client.post(
        "/auth/token",
        data={"username": "other@example.com", "password": "secret123"},
    )
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

    response = await client.get("/products/", headers=other_headers)
    assert response.status_code == 200
    names = [product["name"] for product in response.json()]
    assert "Mouse" in names
