from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID

from sqlalchemy import CHAR, TypeDecorator
from sqlalchemy.engine import Dialect
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base

from consts import DATABASE_URL

Base = declarative_base()


class GUID(TypeDecorator[UUID]):
    """Stores a UUID as a CHAR(36) string; returns a uuid.UUID on read."""

    impl = CHAR(36)
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> str | None:
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value: Any, dialect: Dialect) -> UUID | None:
        if value is None:
            return None
        return UUID(value)


connect_args = {"check_same_thread": False}
engine = create_async_engine(DATABASE_URL, connect_args=connect_args, echo=False)


def _create_session(read_only: bool = False) -> AsyncSession:
    execution_options: dict[str, Any] = {}
    if read_only:
        execution_options["isolation_level"] = "AUTOCOMMIT"

    return AsyncSession(
        bind=engine.execution_options(**execution_options),
        autoflush=True,
        expire_on_commit=False,
    )


def write_session_factory() -> AsyncSession:
    return _create_session()


def read_session_factory() -> AsyncSession:
    return _create_session(read_only=True)


async def get_write_db() -> AsyncGenerator[AsyncSession]:
    async with write_session_factory() as session:
        yield session


async def get_read_db() -> AsyncGenerator[AsyncSession]:
    async with read_session_factory() as session:
        yield session


async def create_db_and_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    await engine.dispose()
