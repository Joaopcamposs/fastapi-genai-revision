from agent.utils import (
    add_to_history,
    clear_chat_history,
    extract_text,
    load_chat_history,
)


def test_extract_text_from_plain_string() -> None:
    assert extract_text("hello world") == "hello world"


def test_extract_text_from_content_blocks() -> None:
    content = [
        {"type": "text", "text": "hello "},
        {"type": "thought_signature", "signature": "abc123"},
        {"type": "text", "text": "world"},
    ]
    assert extract_text(content) == "hello world"


def test_extract_text_from_empty_blocks() -> None:
    assert extract_text([]) == ""


def test_add_and_load_chat_history() -> None:
    user_id = "history-test@example.com"
    clear_chat_history(user_id)
    try:
        add_to_history(user_id, "question 1", "answer 1")
        add_to_history(user_id, "question 2", "answer 2")

        history = load_chat_history(user_id)
        assert len(history) == 2
        assert history[0]["human"] == "question 1"
        assert history[1]["ai"] == "answer 2"
    finally:
        clear_chat_history(user_id)


def test_load_chat_history_for_unknown_user_returns_empty() -> None:
    assert load_chat_history("nobody@example.com") == []


def test_clear_chat_history_removes_file() -> None:
    user_id = "to-clear@example.com"
    add_to_history(user_id, "question", "answer")
    assert load_chat_history(user_id) != []

    clear_chat_history(user_id)
    assert load_chat_history(user_id) == []
