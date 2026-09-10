import json
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, DecimalException

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.schemas.order import TotalRead


class Rate(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    base: str
    quote: str
    rate: Decimal = Field(gt=0, le=1_000_000_000)
    date: date


class CurrencyService:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def convert(self, total: Decimal, currency: str) -> TotalRead:
        if currency == "RUB":
            return TotalRead(currency=currency, total=total)
        try:
            response = await self.client.get(f"rate/RUB/{currency}")
            if response.status_code in {400, 404, 422}:
                raise HTTPException(422, "Currency or exchange rate is not supported")
            response.raise_for_status()
            rate = Rate.model_validate(json.loads(response.text, parse_float=Decimal))
            if rate.base != "RUB" or rate.quote != currency:
                raise ValueError("Unexpected currency pair")
            converted = (total * rate.rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except (httpx.HTTPError, ValidationError, ValueError, DecimalException):
            raise HTTPException(503, "Currency service unavailable") from None
        return TotalRead(currency=currency, total=converted, rate=rate.rate, rate_date=rate.date)
