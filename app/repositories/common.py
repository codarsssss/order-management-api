from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base


async def owned[T: Base](
    session: AsyncSession, model: type[T], resource_id: int, owner_id: int, *, lock: bool = False
) -> T:
    statement = select(model).where(model.id == resource_id, model.owner_id == owner_id)
    if lock:
        statement = statement.with_for_update()
    result = await session.scalar(statement)
    if result is None:
        raise HTTPException(404, f"{model.__name__} not found")
    return result


async def paginate(session: AsyncSession, statement, page: int, page_size: int) -> dict:
    total = await session.scalar(
        select(func.count()).select_from(statement.order_by(None).subquery())
    )
    items = (await session.scalars(statement.offset((page - 1) * page_size).limit(page_size))).all()
    return {"items": items, "page": page, "page_size": page_size, "total": total}


async def update(session: AsyncSession, instance: Base, values: dict) -> Base:
    for key, value in values.items():
        setattr(instance, key, value)
    await session.flush()
    await session.refresh(instance)
    return instance
