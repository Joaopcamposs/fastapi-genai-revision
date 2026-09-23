from httpx import AsyncClient


async def test_get_me_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/users/me")
    assert response.status_code == 401


async def test_get_me_returns_current_user(
    client: AsyncClient, auth_headers: dict
) -> None:
    response = await client.get("/users/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"


async def test_get_own_user(client: AsyncClient, auth_headers: dict) -> None:
    response = await client.get("/users/user@example.com", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"


async def test_get_other_user_forbidden(
    client: AsyncClient, auth_headers: dict
) -> None:
    await client.post(
        "/users/", json={"email": "other@example.com", "password": "secret123"}
    )
    response = await client.get("/users/other@example.com", headers=auth_headers)
    assert response.status_code == 403


async def test_get_own_user_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/users/user@example.com")
    assert response.status_code == 401
