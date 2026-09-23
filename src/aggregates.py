from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class Product:
    """Aggregate root: a sellable product, owned by the tenant (user) that created it."""

    name: str
    price: float
    user_id: UUID
    id: UUID | None = None

    def __post_init__(self) -> None:
        self._validate_name(self.name)
        self._validate_price(self.price)

    @staticmethod
    def _validate_name(name: str) -> None:
        if not name.strip():
            raise ValueError("name cannot be empty")

    @staticmethod
    def _validate_price(price: float) -> None:
        if price < 0:
            raise ValueError("price cannot be negative")

    def rename(self, name: str) -> None:
        self._validate_name(name)
        self.name = name

    def reprice(self, price: float) -> None:
        self._validate_price(price)
        self.price = price


@dataclass
class User:
    """Aggregate root: a registered user. Owns credential invariants."""

    email: str
    password_hash: str
    id: UUID | None = None

    def __post_init__(self) -> None:
        self._validate_email(self.email)
        if not self.password_hash:
            raise ValueError("password_hash cannot be empty")

    @staticmethod
    def _validate_email(email: str) -> None:
        if not email.strip():
            raise ValueError("email cannot be empty")

    def change_email(self, email: str) -> None:
        self._validate_email(email)
        self.email = email

    def change_password(self, password_hash: str) -> None:
        if not password_hash:
            raise ValueError("password_hash cannot be empty")
        self.password_hash = password_hash


@dataclass
class OrderItem:
    product_id: UUID
    quantity: int
    unit_price: float

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.unit_price < 0:
            raise ValueError("unit_price cannot be negative")

    @property
    def subtotal(self) -> float:
        return self.unit_price * self.quantity


@dataclass
class Order:
    """Aggregate root: an order belongs to a user and owns its items."""

    user_id: UUID
    items: list[OrderItem] = field(default_factory=list)
    id: UUID | None = None

    def add_item(self, product_id: UUID, quantity: int, unit_price: float) -> None:
        self.items.append(
            OrderItem(product_id=product_id, quantity=quantity, unit_price=unit_price)
        )

    @property
    def total_amount(self) -> float:
        return sum(item.subtotal for item in self.items)
