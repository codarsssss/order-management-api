from pydantic import EmailStr, Field

from app.schemas.common import Comment, Input, Name, Patch, Timestamped


class CustomerCreate(Input):
    name: Name
    email: EmailStr | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=40)
    comment: Comment | None = None


class CustomerPatch(Patch):
    name: Name | None = None
    email: EmailStr | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=40)
    comment: Comment | None = None


class CustomerRead(Timestamped):
    owner_id: int
    name: str
    email: str | None
    phone: str | None
    comment: str | None
