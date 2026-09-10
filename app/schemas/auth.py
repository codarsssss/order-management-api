from pydantic import ConfigDict, EmailStr, Field, field_validator

from app.schemas.common import Input, Timestamped


class Register(Input):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()


class UserRead(Timestamped):
    email: EmailStr
    is_active: bool


class Token(Input):
    access_token: str
    token_type: str = "bearer"
