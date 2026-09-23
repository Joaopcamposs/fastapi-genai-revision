from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_extensions import uuid7

from infra.database import GUID, Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(GUID, primary_key=True, default=uuid7)
    email: Mapped[str] = mapped_column(Text, unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(Text, nullable=False)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[UUID] = mapped_column(GUID, primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(GUID, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(GUID, primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(GUID, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[UUID] = mapped_column(GUID, primary_key=True, default=uuid7)
    order_id: Mapped[UUID] = mapped_column(
        GUID, ForeignKey("orders.id"), nullable=False
    )
    product_id: Mapped[UUID] = mapped_column(
        GUID, ForeignKey("products.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship(lazy="selectin")
