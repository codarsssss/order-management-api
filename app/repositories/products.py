from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product
from app.repositories.common import paginate


async def list_products(
    session: AsyncSession,
    owner_id: int,
    search: str | None,
    is_active: bool | None,
    min_price: Decimal | None,
    max_price: Decimal | None,
    page: int,
    page_size: int,
) -> dict:
    statement = select(Product).where(Product.owner_id == owner_id)
    if search:
        statement = statement.where(Product.name.icontains(search, autoescape=True))
    if is_active is not None:
        statement = statement.where(Product.is_active == is_active)
    if min_price is not None:
        statement = statement.where(Product.price >= min_price)
    if max_price is not None:
        statement = statement.where(Product.price <= max_price)
    return await paginate(session, statement.order_by(Product.id), page, page_size)
