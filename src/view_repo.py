from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infra.database import read_session_factory
from src.orm_models import Order, Product


class AbstractViewRepo:
    """Owns a read session by default; pass one in to reuse an existing session."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._owns_session = session is None
        self.session = session or read_session_factory()

    async def _release(self) -> None:
        if self._owns_session:
            await self.session.close()


class ProductViewRepo(AbstractViewRepo):
    async def list(self, offset: int = 0, limit: int = 100) -> list[Product]:
        try:
            result = await self.session.execute(
                select(Product).offset(offset).limit(limit)
            )
            return list(result.scalars().all())
        finally:
            await self._release()


class OrderViewRepo(AbstractViewRepo):
    async def list_by_user(
        self, user_id: UUID, offset: int = 0, limit: int = 100
    ) -> list[Order]:
        try:
            result = await self.session.execute(
                select(Order)
                .where(Order.user_id == user_id)
                .offset(offset)
                .limit(limit)
            )
            return list(result.scalars().all())
        finally:
            await self._release()

    async def get_by_id_for_user(self, order_id: UUID, user_id: UUID) -> Order | None:
        try:
            result = await self.session.execute(
                select(Order).where(Order.id == order_id, Order.user_id == user_id)
            )
            return result.scalar_one_or_none()
        finally:
            await self._release()
