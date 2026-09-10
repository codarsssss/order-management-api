from decimal import Decimal

import httpx
import pytest
from fastapi import HTTPException

from app.api.routes.orders import get_currency_service
from app.main import app
from app.services.currency import CurrencyService


async def test_currency_endpoint(client, auth, order):
    calls = []

    def respond(request):
        calls.append(request)
        assert str(request.url) == "https://currency.test/rate/RUB/USD"
        return httpx.Response(
            200, text='{"base":"RUB","quote":"USD","rate":0.0123456789,"date":"2026-09-09"}'
        )

    async with httpx.AsyncClient(
        base_url="https://currency.test/", timeout=1, transport=httpx.MockTransport(respond)
    ) as http:
        app.dependency_overrides[get_currency_service] = lambda: CurrencyService(http)
        path = f"/api/v1/orders/{order['id']}/total"
        rub = await client.get(path, headers=auth[0])
        assert rub.json() == {"currency": "RUB", "total": "37.05"}
        assert not calls
        usd = await client.get(path + "?currency=USD", headers=auth[0])
        assert usd.status_code == 200
        assert usd.json() == {
            "currency": "USD",
            "total": "0.46",
            "rate": "0.0123456789",
            "rate_date": "2026-09-09",
        }
        assert len(calls) == 1
        assert (await client.get(path + "?currency=usd", headers=auth[0])).status_code == 422


@pytest.mark.parametrize(
    "failure,expected",
    [
        ("timeout", 503),
        ("500", 503),
        ("429", 503),
        ("404", 422),
        ("invalid-json", 503),
        ("negative", 503),
        ("wrong-pair", 503),
        ("nan", 503),
    ],
)
async def test_provider_errors(failure, expected):
    def respond(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("timeout", request=request)
        if failure.isdigit():
            return httpx.Response(int(failure))
        if failure == "invalid-json":
            return httpx.Response(200, text="<html>bad gateway</html>")
        return httpx.Response(
            200,
            json={
                "base": "EUR" if failure == "wrong-pair" else "RUB",
                "quote": "USD",
                "rate": "NaN" if failure == "nan" else ("-1" if failure == "negative" else "1"),
                "date": "2026-09-09",
            },
        )

    async with httpx.AsyncClient(
        base_url="https://currency.test/", timeout=1, transport=httpx.MockTransport(respond)
    ) as http:
        with pytest.raises(HTTPException) as error:
            await CurrencyService(http).convert(Decimal("100.00"), "USD")
        assert error.value.status_code == expected
