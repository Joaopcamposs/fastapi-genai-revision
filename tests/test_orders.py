from httpx import AsyncClient


async def _create_product(
    client: AsyncClient, headers: dict, name: str, price: float
) -> str:
    response = await client.post(
        "/products/", json={"name": name, "price": price}, headers=headers
    )
    return response.json()["id"]


async def test_create_order_requires_auth(client: AsyncClient) -> None:
    response = await client.post("/orders/", json={"items": []})
    assert response.status_code == 401


async def test_create_order(client: AsyncClient, auth_headers: dict) -> None:
    product_id = await _create_product(client, auth_headers, "Keyboard", 250.0)
    response = await client.post(
        "/orders/",
        json={"items": [{"product_id": product_id, "quantity": 2}]},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 2
    assert body["items"][0]["unit_price"] == 250.0


async def test_create_order_without_items_fails(
    client: AsyncClient, auth_headers: dict
) -> None:
    response = await client.post("/orders/", json={"items": []}, headers=auth_headers)
    assert response.status_code == 400


async def test_create_order_unknown_product_fails(
    client: AsyncClient, auth_headers: dict
) -> None:
    fake_product_id = "00000000-0000-7000-8000-000000000000"
    response = await client.post(
        "/orders/",
        json={"items": [{"product_id": fake_product_id, "quantity": 1}]},
        headers=auth_headers,
    )
    assert response.status_code == 400


async def test_create_order_with_another_users_product(
    client: AsyncClient, auth_headers: dict
) -> None:
    """Products are public: any user can order a product another user created."""
    product_id = await _create_product(client, auth_headers, "Monitor", 900.0)

    await client.post(
        "/users/", json={"email": "other@example.com", "password": "secret123"}
    )
    other_login = await client.post(
        "/auth/token",
        data={"username": "other@example.com", "password": "secret123"},
    )
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

    response = await client.post(
        "/orders/",
        json={"items": [{"product_id": product_id, "quantity": 1}]},
        headers=other_headers,
    )
    assert response.status_code == 201


async def test_list_orders_scoped_to_current_user(
    client: AsyncClient, auth_headers: dict
) -> None:
    product_id = await _create_product(client, auth_headers, "Mouse", 80.0)
    await client.post(
        "/orders/",
        json={"items": [{"product_id": product_id, "quantity": 1}]},
        headers=auth_headers,
    )

    await client.post(
        "/users/", json={"email": "other@example.com", "password": "secret123"}
    )
    other_login = await client.post(
        "/auth/token",
        data={"username": "other@example.com", "password": "secret123"},
    )
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

    response = await client.get("/orders/", headers=other_headers)
    assert response.status_code == 200
    assert response.json() == []


async def test_get_order_by_id(client: AsyncClient, auth_headers: dict) -> None:
    product_id = await _create_product(client, auth_headers, "Monitor", 900.0)
    create_response = await client.post(
        "/orders/",
        json={"items": [{"product_id": product_id, "quantity": 1}]},
        headers=auth_headers,
    )
    order_id = create_response.json()["id"]

    response = await client.get(f"/orders/{order_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == order_id


async def test_get_order_not_owned_returns_404(
    client: AsyncClient, auth_headers: dict
) -> None:
    product_id = await _create_product(client, auth_headers, "Chair", 500.0)
    create_response = await client.post(
        "/orders/",
        json={"items": [{"product_id": product_id, "quantity": 1}]},
        headers=auth_headers,
    )
    order_id = create_response.json()["id"]

    await client.post(
        "/users/", json={"email": "intruder@example.com", "password": "secret123"}
    )
    intruder_login = await client.post(
        "/auth/token",
        data={"username": "intruder@example.com", "password": "secret123"},
    )
    intruder_headers = {
        "Authorization": f"Bearer {intruder_login.json()['access_token']}"
    }

    response = await client.get(f"/orders/{order_id}", headers=intruder_headers)
    assert response.status_code == 404
