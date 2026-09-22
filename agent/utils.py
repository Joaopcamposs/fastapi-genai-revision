import json
from datetime import UTC, datetime
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage

from consts import CHAT_HISTORY_DIR

CHAT_HISTORY_DIRECTORY = Path(CHAT_HISTORY_DIR)
CHAT_HISTORY_DIRECTORY.mkdir(exist_ok=True)


def extract_text(content: str | list) -> str:
    """Normalize a LangChain message content into plain text.

    Some models (e.g. Gemini 3) return content as a list of content
    blocks instead of a plain string.
    """
    if isinstance(content, str):
        return content
    return "".join(
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    )


def load_chat_history(user_id: str) -> list:
    """Load chat history from the JSON file."""
    file_path = CHAT_HISTORY_DIRECTORY / f"{user_id}.json"
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []


def save_chat_history(user_id: str, history: list) -> None:
    """Save chat history to the JSON file."""
    file_path = CHAT_HISTORY_DIRECTORY / f"{user_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def get_chat_history_for_langchain(user_id: str) -> list:
    """Return chat history as LangChain messages (list of HumanMessage/AIMessage)."""
    history = load_chat_history(user_id)
    langchain_history = []

    # Only the last 10 interactions (20 messages) go into the LLM context
    for msg in history[-10:]:
        langchain_history.append(HumanMessage(content=msg["human"]))
        langchain_history.append(AIMessage(content=msg["ai"]))

    return langchain_history


def add_to_history(user_id: str, human_msg: str, ai_msg: str) -> None:
    """Append an interaction to the user's chat history."""
    history = load_chat_history(user_id)

    history.append(
        {"human": human_msg, "ai": ai_msg, "timestamp": datetime.now(UTC).isoformat()}
    )

    # Cap history at 50 interactions so the file doesn't grow forever
    if len(history) > 50:
        history = history[-50:]

    save_chat_history(user_id, history)


def clear_chat_history(user_id: str) -> None:
    """Delete the user's saved chat history."""
    file_path = CHAT_HISTORY_DIRECTORY / f"{user_id}.json"
    if file_path.exists():
        file_path.unlink()
