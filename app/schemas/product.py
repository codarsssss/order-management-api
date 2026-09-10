from decimal import Decimal

from app.schemas.common import Comment, Input, Money, Name, Patch, Timestamped


class ProductCreate(Input):
    name: Name
    description: Comment | None = None
    price: Money
    is_active: bool = True


class ProductPatch(Patch):
    name: Name | None = None
    description: Comment | None = None
    price: Money | None = None
    is_active: bool | None = None


class ProductRead(Timestamped):
    owner_id: int
    name: str
    description: str | None
    price: Decimal
    is_active: bool
