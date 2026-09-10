from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.security import DUMMY_HASH, create_access_token, password_hash
from app.models import User
from app.schemas.auth import Register


async def register(session: AsyncSession, data: Register) -> User:
    if await session.scalar(select(User.id).where(User.email == data.email)):
        raise HTTPException(409, "Email already registered")
    user = User(
        email=data.email, hashed_password=await run_in_threadpool(password_hash.hash, data.password)
    )
    session.add(user)
    await session.flush()
    return user


async def login(session: AsyncSession, email: str, password: str) -> str:
    user = await session.scalar(select(User).where(User.email == email.strip().lower()))
    valid = await run_in_threadpool(
        password_hash.verify, password, user.hashed_password if user else DUMMY_HASH
    )
    if not valid or user is None:
        raise HTTPException(401, "Invalid credentials", headers={"WWW-Authenticate": "Bearer"})
    if not user.is_active:
        raise HTTPException(403, "User is inactive")
    return create_access_token(user.id)
