from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.api.dependencies import CurrentUser, Session
from app.schemas.auth import Register, Token, UserRead
from app.services import auth

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserRead, status_code=201, summary="Register a user")
async def register(data: Register, session: Session):
    return await auth.register(session, data)


@router.post("/login", response_model=Token, summary="Sign in with email and password")
async def login(session: Session, form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    return Token(access_token=await auth.login(session, form.username, form.password))


@router.get("/me", response_model=UserRead, summary="Get the current user")
async def me(user: CurrentUser):
    return user
