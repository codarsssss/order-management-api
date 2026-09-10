from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, Response

from app.api.dependencies import CurrentUser, PageNumber, PageSize, ResourceId, Session
from app.models import Product
from app.repositories.common import owned, update
from app.repositories.products import list_products
from app.schemas.common import Page
from app.schemas.product import ProductCreate, ProductPatch, ProductRead

router = APIRouter(prefix="/products", tags=["Products"])


@router.post("", response_model=ProductRead, status_code=201, summary="Create a product")
async def create(data: ProductCreate, session: Session, user: CurrentUser):
    resource = Product(owner_id=user.id, **data.model_dump())
    session.add(resource)
    await session.flush()
    return resource


@router.get("", response_model=Page[ProductRead], summary="List and filter products")
async def list_all(
    session: Session,
    user: CurrentUser,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    search: str | None = Query(default=None, max_length=200),
    is_active: bool | None = None,
    min_price: Decimal | None = Query(default=None, ge=0, le=Decimal("9999999999.99")),
    max_price: Decimal | None = Query(default=None, ge=0, le=Decimal("9999999999.99")),
):
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(422, "min_price must not exceed max_price")
    return await list_products(
        session, user.id, search, is_active, min_price, max_price, page, page_size
    )


@router.get("/{resource_id}", response_model=ProductRead, summary="Get a product")
async def get(resource_id: ResourceId, session: Session, user: CurrentUser):
    return await owned(session, Product, resource_id, user.id)


@router.patch("/{resource_id}", response_model=ProductRead, summary="Update a product")
async def patch(resource_id: ResourceId, data: ProductPatch, session: Session, user: CurrentUser):
    resource = await owned(session, Product, resource_id, user.id, lock=True)
    return await update(session, resource, data.model_dump(exclude_unset=True))


@router.delete("/{resource_id}", status_code=204, summary="Delete an unused product")
async def delete(resource_id: ResourceId, session: Session, user: CurrentUser):
    resource = await owned(session, Product, resource_id, user.id, lock=True)
    await session.delete(resource)
    await session.flush()
    return Response(status_code=204)
