from datetime import date
from decimal import Decimal

from pydantic import Field

from app.models.order import OrderStatus
from app.schemas.common import Comment, Input, Patch, Quantity, ReadModel, Timestamped


class ItemCreate(Input):
    product_id: int = Field(gt=0, le=2_147_483_647)
    quantity: Quantity


class ItemPatch(Input):
    quantity: Quantity


class ItemRead(ReadModel):
    id: int
    product_id: int
    quantity: int
    unit_price: Decimal


class OrderCreate(Input):
    customer_id: int = Field(gt=0, le=2_147_483_647)
    comment: Comment | None = None
    items: list[ItemCreate] = Field(default_factory=list, max_length=100)


class OrderPatch(Patch):
    customer_id: int | None = Field(default=None, gt=0, le=2_147_483_647)
    comment: Comment | None = None


class StatusPatch(Input):
    status: OrderStatus


class OrderRead(Timestamped):
    owner_id: int
    customer_id: int
    status: OrderStatus
    comment: str | None
    items: list[ItemRead]
    total: Decimal


class TotalRead(ReadModel):
    currency: str
    total: Decimal
    rate: Decimal | None = None
    rate_date: date | None = None
