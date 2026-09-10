from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Customer
from app.repositories.common import paginate


async def list_customers(
    session: AsyncSession, owner_id: int, search: str | None, page: int, page_size: int
) -> dict:
    statement = select(Customer).where(Customer.owner_id == owner_id)
    if search:
        statement = statement.where(
            or_(
                Customer.name.icontains(search, autoescape=True),
                Customer.email.icontains(search, autoescape=True),
            )
        )
    return await paginate(session, statement.order_by(Customer.id), page, page_size)
