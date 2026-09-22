import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from agent.llm import build_agent
from agent.schemas import AgentRequest, AgentResponse
from agent.tools import build_tools
from agent.utils import (
    add_to_history,
    clear_chat_history,
    extract_text,
    get_chat_history_for_langchain,
    load_chat_history,
)
from src.entry_points import CurrentUser

agent_router = APIRouter(prefix="/agent", tags=["agent"])


@agent_router.post("/ask", response_model=AgentResponse)
async def ask(payload: AgentRequest, current_user: CurrentUser) -> AgentResponse:
    history = get_chat_history_for_langchain(current_user.email)
    messages = history + [HumanMessage(content=payload.question)]

    agent = build_agent(build_tools(current_user.id))
    result = await agent.ainvoke({"messages": messages})
    answer = extract_text(result["messages"][-1].content)

    add_to_history(current_user.email, payload.question, answer)
    return AgentResponse(answer=answer)


@agent_router.post("/ask/stream")
async def ask_stream(
    payload: AgentRequest, current_user: CurrentUser
) -> StreamingResponse:
    history = get_chat_history_for_langchain(current_user.email)
    messages = history + [HumanMessage(content=payload.question)]
    agent = build_agent(build_tools(current_user.id))

    async def event_stream() -> AsyncGenerator[str]:
        answer = ""
        async for event in agent.astream_events({"messages": messages}):
            if event["event"] != "on_chat_model_stream":
                continue
            content = extract_text(event["data"]["chunk"].content)
            if not content:
                continue
            answer += content
            yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"

        add_to_history(current_user.email, payload.question, answer)
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@agent_router.get("/history")
async def get_history(current_user: CurrentUser) -> dict:
    history = load_chat_history(current_user.email)
    return {"history": history, "total": len(history)}


@agent_router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
async def delete_history(current_user: CurrentUser) -> None:
    clear_chat_history(current_user.email)
