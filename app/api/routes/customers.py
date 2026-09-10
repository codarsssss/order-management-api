from fastapi import APIRouter, Query, Response

from app.api.dependencies import CurrentUser, PageNumber, PageSize, ResourceId, Session
from app.models import Customer
from app.repositories.common import owned, update
from app.repositories.customers import list_customers
from app.schemas.common import Page
from app.schemas.customer import CustomerCreate, CustomerPatch, CustomerRead

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.post("", response_model=CustomerRead, status_code=201, summary="Create a customer")
async def create(data: CustomerCreate, session: Session, user: CurrentUser):
    resource = Customer(owner_id=user.id, **data.model_dump())
    session.add(resource)
    await session.flush()
    return resource


@router.get("", response_model=Page[CustomerRead], summary="List and filter customers")
async def list_all(
    session: Session,
    user: CurrentUser,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    search: str | None = Query(default=None, max_length=200),
):
    return await list_customers(session, user.id, search, page, page_size)


@router.get("/{resource_id}", response_model=CustomerRead, summary="Get a customer")
async def get(resource_id: ResourceId, session: Session, user: CurrentUser):
    return await owned(session, Customer, resource_id, user.id)


@router.patch("/{resource_id}", response_model=CustomerRead, summary="Update a customer")
async def patch(resource_id: ResourceId, data: CustomerPatch, session: Session, user: CurrentUser):
    resource = await owned(session, Customer, resource_id, user.id, lock=True)
    return await update(session, resource, data.model_dump(exclude_unset=True))


@router.delete("/{resource_id}", status_code=204, summary="Delete an unused customer")
async def delete(resource_id: ResourceId, session: Session, user: CurrentUser):
    resource = await owned(session, Customer, resource_id, user.id, lock=True)
    await session.delete(resource)
    await session.flush()
    return Response(status_code=204)
