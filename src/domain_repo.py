from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infra.database import write_session_factory
from src.aggregates import Order as OrderAggregate
from src.aggregates import Product as ProductAggregate
from src.aggregates import User as UserAggregate
from src.orm_models import Order, OrderItem, Product, User


class AbstractDomainRepo:
    """Owns a write session by default; pass one in to reuse an existing transaction."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._owns_session = session is None
        self.session = session or write_session_factory()

    async def _release(self) -> None:
        if self._owns_session:
            await self.session.close()


class UserRepository(AbstractDomainRepo):
    """Persists the User aggregate, translating to/from the ORM model."""

    async def add(self, user: UserAggregate) -> User:
        try:
            db_user = User(email=user.email, password=user.password_hash)
            self.session.add(db_user)
            await self.session.commit()
            await self.session.refresh(db_user)
            return db_user
        finally:
            await self._release()

    async def get_by_email(self, email: str) -> User | None:
        try:
            result = await self.session.execute(select(User).where(User.email == email))
            return result.scalar_one_or_none()
        finally:
            await self._release()

    async def list(self, offset: int = 0, limit: int = 100) -> list[User]:
        try:
            result = await self.session.execute(
                select(User).offset(offset).limit(limit)
            )
            return list(result.scalars().all())
        finally:
            await self._release()


class ProductRepository(AbstractDomainRepo):
    """Persists the Product aggregate, translating to/from the ORM model."""

    async def add(self, product: ProductAggregate) -> Product:
        try:
            db_product = Product(name=product.name, price=product.price)
            self.session.add(db_product)
            await self.session.commit()
            await self.session.refresh(db_product)
            return db_product
        finally:
            await self._release()

    async def get_by_id(self, product_id: UUID) -> Product | None:
        try:
            return await self.session.get(Product, product_id)
        finally:
            await self._release()


class OrderRepository(AbstractDomainRepo):
    """Persists the Order aggregate, translating to/from the ORM model."""

    async def add(self, order: OrderAggregate) -> Order:
        try:
            db_order = Order(
                user_id=order.user_id,
                items=[
                    OrderItem(
                        product_id=item.product_id,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                    )
                    for item in order.items
                ],
            )
            self.session.add(db_order)
            await self.session.commit()
            await self.session.refresh(db_order)
            return db_order
        finally:
            await self._release()

    async def get_by_id(self, order_id: UUID) -> Order | None:
        try:
            return await self.session.get(Order, order_id)
        finally:
            await self._release()
