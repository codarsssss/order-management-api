"""Create a demo account once. Set DEMO_EMAIL and DEMO_PASSWORD explicitly."""

import asyncio
import os
from decimal import Decimal

from sqlalchemy import select

from app.db.session import engine, session_factory
from app.models import Customer, Product, User
from app.schemas.auth import Register
from app.schemas.order import ItemCreate, OrderCreate
from app.services.auth import register
from app.services.orders import create


async def main() -> None:
    data = Register(email=os.environ["DEMO_EMAIL"], password=os.environ["DEMO_PASSWORD"])
    try:
        async with session_factory() as session, session.begin():
            if await session.scalar(select(User.id).where(User.email == data.email)):
                return
            user = await register(session, data)
            customer = Customer(owner_id=user.id, name="Acme Studio", email="client@example.com")
            product = Product(
                owner_id=user.id, name="Backend consultation", price=Decimal("5000.00")
            )
            session.add_all([customer, product])
            await session.flush()
            await create(
                session,
                user.id,
                OrderCreate(
                    customer_id=customer.id,
                    comment="Demo order",
                    items=[ItemCreate(product_id=product.id, quantity=2)],
                ),
            )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
