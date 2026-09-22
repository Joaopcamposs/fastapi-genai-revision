from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from agent.llm import ensure_configured
from agent.routes import agent_router
from infra.database import create_db_and_tables, dispose_engine
from src.entry_points import auth_router, order_router, product_router, user_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    ensure_configured()
    await create_db_and_tables()
    yield
    await dispose_engine()


app = FastAPI(
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True},
)

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(product_router)
app.include_router(order_router)
app.include_router(agent_router)
