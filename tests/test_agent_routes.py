import json

import pytest
from httpx import AsyncClient
from langchain_core.messages import AIMessage, AIMessageChunk

import agent.routes as agent_routes


class FakeAgent:
    """Stands in for the real LangChain agent so tests don't call the Gemini API."""

    def __init__(self, answer: str = "fake answer") -> None:
        self.answer = answer

    async def ainvoke(self, state: dict) -> dict:
        return {"messages": [AIMessage(content=self.answer)]}

    async def astream_events(self, state: dict, **kwargs):
        for word in self.answer.split(" "):
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": AIMessageChunk(content=word + " ")},
            }


@pytest.fixture(autouse=True)
def _fake_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_routes, "build_agent", lambda tools: FakeAgent())


async def test_ask_requires_auth(client: AsyncClient) -> None:
    response = await client.post("/agent/ask", json={"question": "hi"})
    assert response.status_code == 401


async def test_ask_returns_answer_and_saves_history(
    client: AsyncClient, auth_headers: dict
) -> None:
    response = await client.post(
        "/agent/ask", json={"question": "What products exist?"}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json() == {"answer": "fake answer"}

    history = await client.get("/agent/history", headers=auth_headers)
    assert history.status_code == 200
    body = history.json()
    assert body["total"] == 1
    assert body["history"][0]["human"] == "What products exist?"
    assert body["history"][0]["ai"] == "fake answer"


async def test_ask_stream_requires_auth(client: AsyncClient) -> None:
    response = await client.post("/agent/ask/stream", json={"question": "hi"})
    assert response.status_code == 401


async def test_ask_stream_returns_sse_events(
    client: AsyncClient, auth_headers: dict
) -> None:
    async with client.stream(
        "POST",
        "/agent/ask/stream",
        json={"question": "hi"},
        headers=auth_headers,
    ) as response:
        assert response.status_code == 200
        lines = [line async for line in response.aiter_lines() if line]

    assert lines[-1] == "data: [DONE]"
    content_lines = [json.loads(line.removeprefix("data: ")) for line in lines[:-1]]
    assert "".join(chunk["content"] for chunk in content_lines) == "fake answer "


async def test_get_history_empty_by_default(
    client: AsyncClient, auth_headers: dict
) -> None:
    response = await client.get("/agent/history", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"history": [], "total": 0}


async def test_delete_history(client: AsyncClient, auth_headers: dict) -> None:
    await client.post("/agent/ask", json={"question": "hi"}, headers=auth_headers)

    response = await client.delete("/agent/history", headers=auth_headers)
    assert response.status_code == 204

    history = await client.get("/agent/history", headers=auth_headers)
    assert history.json() == {"history": [], "total": 0}
