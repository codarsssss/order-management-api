from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
Name = Annotated[str, Field(min_length=1, max_length=200)]
Comment = Annotated[str, Field(max_length=5000)]
Quantity = Annotated[int, Field(gt=0, le=1_000_000, strict=True)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Patch(Input):
    @model_validator(mode="after")
    def reject_null_required_fields(self):
        for name in self.model_fields_set:
            if (
                name in {"name", "price", "is_active", "customer_id"}
                and getattr(self, name) is None
            ):
                raise ValueError(f"{name} cannot be null")
        return self


class ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Timestamped(ReadModel):
    id: int
    created_at: datetime
    updated_at: datetime


class Page[T](BaseModel):
    items: list[T]
    page: int
    page_size: int
    total: int


class Error(BaseModel):
    detail: str
