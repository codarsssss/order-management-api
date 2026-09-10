from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import AwareDatetime

from app.api.dependencies import CurrentUser, PageNumber, PageSize, ResourceId, Session
from app.models import OrderStatus
from app.repositories.orders import get_order, list_orders
from app.schemas.common import Page
from app.schemas.order import (
    ItemCreate,
    ItemPatch,
    OrderCreate,
    OrderPatch,
    OrderRead,
    StatusPatch,
    TotalRead,
)
from app.services import orders
from app.services.currency import CurrencyService

router = APIRouter(prefix="/orders", tags=["Orders"])


def get_currency_service(request: Request) -> CurrencyService:
    return CurrencyService(request.app.state.currency_client)


@router.post("", response_model=OrderRead, status_code=201, summary="Create an order atomically")
async def create(data: OrderCreate, session: Session, user: CurrentUser):
    return await orders.create(session, user.id, data)


@router.get("", response_model=Page[OrderRead], summary="List, filter and sort orders")
async def list_all(
    session: Session,
    user: CurrentUser,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    status: OrderStatus | None = None,
    customer_id: int | None = Query(default=None, gt=0, le=2_147_483_647),
    date_from: AwareDatetime | None = None,
    date_to: AwareDatetime | None = None,
    sort: Literal["created_at", "-created_at", "total", "-total"] = "-created_at",
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, "date_from must not exceed date_to")
    return await list_orders(
        session, user.id, status, customer_id, date_from, date_to, sort, page, page_size
    )


@router.get("/{order_id}", response_model=OrderRead, summary="Get an order with items and total")
async def get(order_id: ResourceId, session: Session, user: CurrentUser):
    return await get_order(session, order_id, user.id)


@router.patch("/{order_id}", response_model=OrderRead, summary="Update a new order")
async def patch(order_id: ResourceId, data: OrderPatch, session: Session, user: CurrentUser):
    order = await get_order(session, order_id, user.id, lock=True)
    return await orders.patch(session, order, data)


@router.delete("/{order_id}", status_code=204, summary="Delete a new order")
async def delete(order_id: ResourceId, session: Session, user: CurrentUser):
    order = await get_order(session, order_id, user.id, lock=True)
    orders.require_editable(order)
    await session.delete(order)
    await session.flush()
    return Response(status_code=204)


@router.post(
    "/{order_id}/items",
    response_model=OrderRead,
    status_code=201,
    summary="Add an item using the current product price",
)
async def add_item(order_id: ResourceId, data: ItemCreate, session: Session, user: CurrentUser):
    order = await get_order(session, order_id, user.id, lock=True)
    return await orders.add_item(session, order, data)


@router.patch(
    "/{order_id}/items/{item_id}", response_model=OrderRead, summary="Change an item quantity"
)
async def patch_item(
    order_id: ResourceId, item_id: ResourceId, data: ItemPatch, session: Session, user: CurrentUser
):
    order = await get_order(session, order_id, user.id, lock=True)
    orders.find_item(order, item_id).quantity = data.quantity
    return await orders.save(session, order)


@router.delete("/{order_id}/items/{item_id}", status_code=204, summary="Remove an order item")
async def delete_item(
    order_id: ResourceId, item_id: ResourceId, session: Session, user: CurrentUser
):
    order = await get_order(session, order_id, user.id, lock=True)
    order.items.remove(orders.find_item(order, item_id))
    await orders.save(session, order)
    return Response(status_code=204)


@router.patch("/{order_id}/status", response_model=OrderRead, summary="Transition the order status")
async def status(order_id: ResourceId, data: StatusPatch, session: Session, user: CurrentUser):
    order = await get_order(session, order_id, user.id, lock=True)
    return await orders.change_status(session, order, data.status)


@router.get(
    "/{order_id}/total",
    response_model=TotalRead,
    response_model_exclude_none=True,
    summary="Get the RUB total or convert using a reference exchange rate",
)
async def total(
    order_id: ResourceId,
    session: Session,
    user: CurrentUser,
    service: Annotated[CurrencyService, Depends(get_currency_service)],
    currency: str = Query(default="RUB", pattern="^[A-Z]{3}$"),
):
    order = await get_order(session, order_id, user.id)
    return await service.convert(order.total, currency)
