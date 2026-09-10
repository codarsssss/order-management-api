from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models import Order, User
from scripts import seed


async def test_demo_seed_is_atomic_and_idempotent(db_factory, monkeypatch):
    monkeypatch.setenv("DEMO_EMAIL", "demo@example.com")
    monkeypatch.setenv("DEMO_PASSWORD", "secure-demo-password")
    monkeypatch.setattr(seed, "session_factory", db_factory)
    await seed.main()
    await seed.main()
    async with db_factory() as session:
        assert await session.scalar(select(func.count()).select_from(User)) == 1
        order = await session.scalar(select(Order).options(selectinload(Order.items)))
        assert order.total == Decimal("10000.00")
