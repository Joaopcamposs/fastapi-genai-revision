from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from infra.security import SecurityServices
from src.domain_repo import OrderRepository, ProductRepository, UserRepository
from src.orm_models import User
from src.schemas import (
    OrderCreate,
    OrderPublic,
    ProductCreate,
    ProductPublic,
    Token,
    UserCreate,
    UserPublic,
)
from src.services import AuthService, OrderService, ProductService, UserService
from src.view_repo import OrderViewRepo, ProductViewRepo

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    email = SecurityServices.decode_access_token(token)
    if email is None:
        raise credentials_error
    user = await UserRepository().get_by_email(email)
    if user is None:
        raise credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def ensure_self(current_user: User, email: str) -> None:
    if current_user.email != email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="not allowed to access this user",
        )


auth_router = APIRouter(prefix="/auth", tags=["auth"])
user_router = APIRouter(prefix="/users", tags=["users"])
product_router = APIRouter(prefix="/products", tags=["products"])
order_router = APIRouter(prefix="/orders", tags=["orders"])


@auth_router.post("/token", response_model=Token)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    auth_service = AuthService(UserRepository())
    user = await auth_service.authenticate(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=auth_service.login(user))


@user_router.post("/", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate) -> User:
    try:
        return await UserService(UserRepository()).create(
            payload.email, payload.password
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@user_router.get("/", response_model=list[UserPublic])
async def list_users(
    current_user: CurrentUser,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> list[User]:
    return await UserService(UserRepository()).list(offset=offset, limit=limit)


@user_router.get("/{email}", response_model=UserPublic)
async def get_user(email: str, current_user: CurrentUser) -> User:
    ensure_self(current_user, email)
    user = await UserService(UserRepository()).get_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="user not found"
        )
    return user


@product_router.post(
    "/", response_model=ProductPublic, status_code=status.HTTP_201_CREATED
)
async def create_product(
    payload: ProductCreate, current_user: CurrentUser
) -> ProductPublic:
    try:
        product = await ProductService(ProductRepository()).create(
            payload.name, payload.price
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    return ProductPublic.model_validate(product)


@product_router.get("/", response_model=list[ProductPublic])
async def list_products(
    current_user: CurrentUser,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> list[ProductPublic]:
    products = await ProductViewRepo().list(offset=offset, limit=limit)
    return [ProductPublic.model_validate(product) for product in products]


@order_router.post("/", response_model=OrderPublic, status_code=status.HTTP_201_CREATED)
async def create_order(payload: OrderCreate, current_user: CurrentUser) -> OrderPublic:
    order_service = OrderService(OrderRepository(), ProductRepository())
    try:
        order = await order_service.create_order(current_user.id, payload.items)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    return OrderPublic.model_validate(order)


@order_router.get("/", response_model=list[OrderPublic])
async def list_orders(
    current_user: CurrentUser,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> list[OrderPublic]:
    orders = await OrderViewRepo().list_by_user(
        current_user.id, offset=offset, limit=limit
    )
    return [OrderPublic.model_validate(order) for order in orders]


@order_router.get("/{order_id}", response_model=OrderPublic)
async def get_order(order_id: UUID, current_user: CurrentUser) -> OrderPublic:
    order = await OrderViewRepo().get_by_id_for_user(order_id, current_user.id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="order not found"
        )
    return OrderPublic.model_validate(order)
