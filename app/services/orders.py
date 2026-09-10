from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Customer, Order, OrderItem, OrderStatus
from app.repositories.common import owned
from app.repositories.orders import get_products
from app.schemas.order import ItemCreate, OrderCreate, OrderPatch

TRANSITIONS = {
    OrderStatus.new: {OrderStatus.confirmed, OrderStatus.cancelled},
    OrderStatus.confirmed: {OrderStatus.processing, OrderStatus.cancelled},
    OrderStatus.processing: {OrderStatus.completed, OrderStatus.cancelled},
    OrderStatus.completed: set(),
    OrderStatus.cancelled: set(),
}


def require_editable(order: Order) -> None:
    if order.status != OrderStatus.new:
        raise HTTPException(409, "Only new orders can be edited or deleted")


async def save(session: AsyncSession, order: Order) -> Order:
    order.updated_at = datetime.now(UTC)
    await session.flush()
    return order


async def create(session: AsyncSession, owner_id: int, data: OrderCreate) -> Order:
    await owned(session, Customer, data.customer_id, owner_id)
    products = await get_products(session, owner_id, {item.product_id for item in data.items})
    order = Order(owner_id=owner_id, customer_id=data.customer_id, comment=data.comment, items=[])
    session.add(order)
    for item in data.items:
        order.items.append(
            OrderItem(
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=products[item.product_id].price,
            )
        )
    await session.flush()
    return order


async def patch(session: AsyncSession, order: Order, data: OrderPatch) -> Order:
    require_editable(order)
    values = data.model_dump(exclude_unset=True)
    if "customer_id" in values:
        await owned(session, Customer, values["customer_id"], order.owner_id)
    for key, value in values.items():
        setattr(order, key, value)
    return await save(session, order)


async def add_item(session: AsyncSession, order: Order, data: ItemCreate) -> Order:
    require_editable(order)
    if len(order.items) >= 100:
        raise HTTPException(409, "Order cannot contain more than 100 items")
    products = await get_products(session, order.owner_id, {data.product_id})
    order.items.append(
        OrderItem(
            product_id=data.product_id,
            quantity=data.quantity,
            unit_price=products[data.product_id].price,
        )
    )
    return await save(session, order)


def find_item(order: Order, item_id: int) -> OrderItem:
    require_editable(order)
    for item in order.items:
        if item.id == item_id:
            return item
    raise HTTPException(404, "Order item not found")


async def change_status(session: AsyncSession, order: Order, status: OrderStatus) -> Order:
    if status not in TRANSITIONS[order.status]:
        raise HTTPException(409, "Invalid order status transition")
    if status == OrderStatus.confirmed and not order.items:
        raise HTTPException(409, "Cannot confirm an empty order")
    order.status = status
    return await save(session, order)
