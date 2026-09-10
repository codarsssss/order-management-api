from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Order, OrderItem, OrderStatus, Product
from app.repositories.common import paginate


async def get_order(
    session: AsyncSession, order_id: int, owner_id: int, *, lock: bool = False
) -> Order:
    statement = select(Order).where(Order.id == order_id, Order.owner_id == owner_id)
    if lock:
        statement = statement.with_for_update()
    order = await session.scalar(statement.options(selectinload(Order.items)))
    if order is None:
        raise HTTPException(404, "Order not found")
    return order


async def get_products(session: AsyncSession, owner_id: int, ids: set[int]) -> dict[int, Product]:
    # Deterministic locking order avoids deadlocks between multi-product orders.
    products = (
        await session.scalars(
            select(Product)
            .where(Product.owner_id == owner_id, Product.id.in_(ids))
            .order_by(Product.id)
            .with_for_update()
        )
    ).all()
    if len(products) != len(ids):
        raise HTTPException(404, "Product not found")
    if any(not product.is_active for product in products):
        raise HTTPException(409, "Product is inactive")
    return {product.id: product for product in products}


async def list_orders(
    session: AsyncSession,
    owner_id: int,
    status: OrderStatus | None,
    customer_id: int | None,
    date_from: datetime | None,
    date_to: datetime | None,
    sort: str,
    page: int,
    page_size: int,
) -> dict:
    statement = select(Order).where(Order.owner_id == owner_id)
    if status is not None:
        statement = statement.where(Order.status == status)
    if customer_id is not None:
        statement = statement.where(Order.customer_id == customer_id)
    if date_from is not None:
        statement = statement.where(Order.created_at >= date_from)
    if date_to is not None:
        statement = statement.where(Order.created_at <= date_to)
    total = (
        select(func.coalesce(func.sum(OrderItem.quantity * OrderItem.unit_price), 0))
        .where(OrderItem.order_id == Order.id)
        .scalar_subquery()
    )
    column = total if sort.lstrip("-") == "total" else Order.created_at
    statement = statement.order_by(column.desc() if sort.startswith("-") else column, Order.id)
    return await paginate(session, statement.options(selectinload(Order.items)), page, page_size)
