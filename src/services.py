from uuid import UUID

from infra.security import SecurityServices
from src.aggregates import Order as OrderAggregate
from src.aggregates import Product as ProductAggregate
from src.aggregates import User as UserAggregate
from src.domain_repo import OrderRepository, ProductRepository, UserRepository
from src.orm_models import Order, Product, User
from src.schemas import OrderItemCreate


class UserService:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    async def create(self, email: str, password: str) -> User:
        if await self.user_repo.get_by_email(email):
            raise ValueError("email already registered")
        user = UserAggregate(
            email=email, password_hash=SecurityServices.encrypt_password(password)
        )
        return await self.user_repo.add(user)

    async def get_by_email(self, email: str) -> User | None:
        return await self.user_repo.get_by_email(email)

    async def list(self, offset: int = 0, limit: int = 100) -> list[User]:
        return await self.user_repo.list(offset=offset, limit=limit)


class AuthService:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    @staticmethod
    def _has_valid_credentials(user: User | None, password: str) -> bool:
        return bool(
            user
            and user.password
            and SecurityServices.verify_password(password, user.password)
        )

    async def authenticate(self, email: str, password: str) -> User | None:
        user = await self.user_repo.get_by_email(email)
        if not self._has_valid_credentials(user, password):
            return None
        return user

    @staticmethod
    def login(user: User) -> str:
        return SecurityServices.create_access_token(subject=user.email)


class ProductService:
    def __init__(self, product_repo: ProductRepository) -> None:
        self.product_repo = product_repo

    async def create(self, name: str, price: float) -> Product:
        product = ProductAggregate(name=name, price=price)
        return await self.product_repo.add(product)


class OrderService:
    def __init__(
        self, order_repo: OrderRepository, product_repo: ProductRepository
    ) -> None:
        self.order_repo = order_repo
        self.product_repo = product_repo

    async def create_order(self, user_id: UUID, items: list[OrderItemCreate]) -> Order:
        if not items:
            raise ValueError("order must have at least one item")

        order = OrderAggregate(user_id=user_id)
        for item in items:
            product = await self.product_repo.get_by_id(item.product_id)
            if not product:
                raise ValueError(f"product {item.product_id} not found")
            order.add_item(
                product_id=product.id,
                quantity=item.quantity,
                unit_price=float(product.price),
            )

        return await self.order_repo.add(order)
