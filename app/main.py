from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import text

from app.api.dependencies import Session
from app.api.routes import auth, customers, orders, products
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.db.session import engine
from app.schemas.common import Error

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(
        base_url=settings.currency_api_url.rstrip("/") + "/",
        timeout=settings.currency_timeout_seconds,
    ) as client:
        app.state.currency_client = client
        yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
    description="Manage your customers, products and transactional orders. All prices are in RUB.",
    responses={code: {"model": Error} for code in (400, 401, 403, 404, 409, 503)},
)
register_exception_handlers(app)
for router in (auth.router, customers.router, products.router, orders.router):
    app.include_router(router, prefix="/api/v1")


class Health(BaseModel):
    status: str = "ok"
    database: str = "ok"


@app.get("/health", tags=["System"], response_model=Health, summary="Check API and database health")
async def health(session: Session):
    await session.execute(text("SELECT 1"))
    return Health()
