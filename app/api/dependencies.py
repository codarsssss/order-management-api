from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Path, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_session
from app.models import User

Session = Annotated[AsyncSession, Depends(get_session, scope="function")]
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def current_user(session: Session, token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    try:
        user_id = decode_access_token(token)
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise HTTPException(
            401, "Invalid credentials", headers={"WWW-Authenticate": "Bearer"}
        ) from None
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(401, "Invalid credentials", headers={"WWW-Authenticate": "Bearer"})
    if not user.is_active:
        raise HTTPException(403, "User is inactive")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
PageNumber = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]
ResourceId = Annotated[int, Path(gt=0, le=2_147_483_647)]
