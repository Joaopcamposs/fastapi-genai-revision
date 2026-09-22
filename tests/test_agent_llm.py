import pytest

import agent.llm as agent_llm


def test_ensure_configured_passes_when_key_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(agent_llm, "GOOGLE_API_KEY", "some-key")
    agent_llm.ensure_configured()


def test_ensure_configured_raises_when_key_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(agent_llm, "GOOGLE_API_KEY", None)
    with pytest.raises(RuntimeError):
        agent_llm.ensure_configured()
