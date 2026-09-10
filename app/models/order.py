from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps

if TYPE_CHECKING:
    from app.models.order_item import OrderItem


class OrderStatus(StrEnum):
    new = "new"
    confirmed = "confirmed"
    processing = "processing"
    completed = "completed"
    cancelled = "cancelled"


class Order(Timestamps, Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_owner_created", "owner_id", "created_at"),
        Index("ix_orders_owner_status", "owner_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"), default=OrderStatus.new, server_default="new"
    )
    comment: Mapped[str | None] = mapped_column(Text)
    items: Mapped[list["OrderItem"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, lazy="raise", order_by="OrderItem.id"
    )

    @property
    def total(self) -> Decimal:
        return sum((item.unit_price * item.quantity for item in self.items), Decimal("0.00"))
