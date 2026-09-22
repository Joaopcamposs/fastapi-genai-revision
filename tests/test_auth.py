from httpx import AsyncClient


async def test_register_user(client: AsyncClient) -> None:
    response = await client.post(
        "/users/", json={"email": "new@example.com", "password": "secret123"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new@example.com"
    assert "id" in body


async def test_register_duplicate_email_fails(client: AsyncClient) -> None:
    await client.post(
        "/users/", json={"email": "dup@example.com", "password": "secret123"}
    )
    response = await client.post(
        "/users/", json={"email": "dup@example.com", "password": "other-password"}
    )
    assert response.status_code == 400


async def test_login_success(client: AsyncClient) -> None:
    await client.post(
        "/users/", json={"email": "login@example.com", "password": "secret123"}
    )
    response = await client.post(
        "/auth/token",
        data={"username": "login@example.com", "password": "secret123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


async def test_login_wrong_password_fails(client: AsyncClient) -> None:
    await client.post(
        "/users/", json={"email": "login2@example.com", "password": "secret123"}
    )
    response = await client.post(
        "/auth/token",
        data={"username": "login2@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


async def test_login_unknown_user_fails(client: AsyncClient) -> None:
    response = await client.post(
        "/auth/token",
        data={"username": "ghost@example.com", "password": "secret123"},
    )
    assert response.status_code == 401
