from datetime import UTC, datetime

from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from consts import GOOGLE_API_KEY, LLM_MODEL

llm = ChatGoogleGenerativeAI(
    model=LLM_MODEL,
    temperature=0.2,
    google_api_key=GOOGLE_API_KEY,
    timeout=30,
    max_retries=2,
)


def ensure_configured() -> None:
    """Fail fast at startup if the agent's API key is missing."""
    if not GOOGLE_API_KEY:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set; the agent endpoints will not work."
        )


SYSTEM_PROMPT = """You are a shopping assistant. You answer questions about \
available products and about the authenticated user's own orders.

Current date/time: {now}

Always use the tools to answer — never invent products, prices or orders."""


def build_agent(tools: list):
    """Create a ReAct agent with the tools given for the current request."""
    system_prompt = SYSTEM_PROMPT.format(now=datetime.now(UTC).isoformat())
    return create_agent(llm, tools, system_prompt=system_prompt)
