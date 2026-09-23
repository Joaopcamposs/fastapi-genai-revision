from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from agent.llm import ensure_configured
from agent.routes import agent_router
from infra.database import create_db_and_tables, dispose_engine
from infra.rate_limit import limiter
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
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(product_router)
app.include_router(order_router)
app.include_router(agent_router)
