"""Responses carrying fields a newer API version added must not raise.

Every hand-written resource method is exercised through the real client with
respx, sync and async, with an extra unknown key injected into the payload.
"""
import asyncio

import httpx
import pytest
import respx

from form4api import Company, Form4ApiClient, Insider, InsiderSignal
from form4api._client import AsyncForm4ApiClient
from form4api._types import WebhookCreated, WebhookEvent, WebhookSubscription

BASE = "https://api.form4api.com"
NEW = {"somethingNewFromTheBackend": 1, "anotherNewThing": {"nested": [1, 2]}}

INSIDER = {
    "cik": "0001214156",
    "name": "Cook Timothy D",
    "isDirector": False,
    "isOfficer": True,
    "isTenPercentOwner": False,
    "officerTitle": "CEO",
    "totalFilings": 42,
    **NEW,
}
COMPANY = {
    "cik": "0000320193",
    "name": "Apple Inc.",
    "ticker": "AAPL",
    "exchange": "NASDAQ",
    "totalFilings": 100,
    "activeInsiders": 12,
    "sicDescription": "Electronic Computers",
    "stateOfIncorporation": "CA",
    "website": None,
    **NEW,
}
SIGNAL = {
    "ticker": "AAPL",
    "companyName": "Apple Inc.",
    "signalDate": "2026-01-15",
    "buySellRatio": 2.5,
    "isClusterBuy": True,
    "isClusterSell": False,
    "insiderCount": 4,
    **NEW,
}
WH_CREATED = {
    "subscriptionId": 7,
    "url": "https://example.com/hook",
    "eventTypes": ["Form4Filed"],
    "secret": "s3cret",
    "createdAt": "2026-01-15T00:00:00Z",
    "warning": None,
    **NEW,
}
WH_SUB = {
    "subscriptionId": 7,
    "url": "https://example.com/hook",
    "eventTypes": ["Form4Filed"],
    "createdAt": "2026-01-15T00:00:00Z",
    "isActive": True,
    **NEW,
}
WH_EVENT = {
    "deliveryId": 9,
    "subscriptionId": 7,
    "eventType": "Form4Filed",
    "attemptCount": 1,
    "deliveredAt": None,
    "nextRetryAt": None,
    "lastStatusCode": 500,
    "isDead": False,
    "payload": "{}",
    **NEW,
}


@pytest.fixture
def client():
    with Form4ApiClient("test-key", max_retries=0) as c:
        yield c


def run_async(fn):
    async def go():
        async with AsyncForm4ApiClient("test-key", max_retries=0) as c:
            return await fn(c)

    return asyncio.run(go())


def check_insider(i):
    assert isinstance(i, Insider)
    assert i.cik == "0001214156" and i.name == "Cook Timothy D"
    assert i.is_officer is True and i.officer_title == "CEO" and i.total_filings == 42
    assert not hasattr(i, "something_new_from_the_backend")


def check_company(c):
    assert isinstance(c, Company)
    assert c.ticker == "AAPL" and c.active_insiders == 12 and c.total_filings == 100
    assert c.sic_description == "Electronic Computers"


def check_signal(s):
    assert isinstance(s, InsiderSignal)
    assert s.ticker == "AAPL" and s.buy_sell_ratio == 2.5 and s.is_cluster_buy is True
    assert s.insider_count == 4


def check_created(w):
    assert isinstance(w, WebhookCreated)
    assert w.subscription_id == 7 and w.secret == "s3cret" and w.event_types == ["Form4Filed"]


def check_sub(w):
    assert isinstance(w, WebhookSubscription)
    assert w.subscription_id == 7 and w.is_active is True and w.created_at.startswith("2026")


def check_event(e):
    assert isinstance(e, WebhookEvent)
    assert e.delivery_id == 9 and e.last_status_code == 500 and e.payload == "{}"


# ── sync ─────────────────────────────────────────────────────────────────────

@respx.mock
def test_companies_get_ignores_unknown_fields(client):
    respx.get(f"{BASE}/v1/companies/AAPL").mock(return_value=httpx.Response(200, json=COMPANY))
    check_company(client.companies.get("AAPL"))


@respx.mock
def test_companies_insiders_ignores_unknown_fields(client):
    respx.get(f"{BASE}/v1/companies/AAPL/insiders").mock(return_value=httpx.Response(200, json=[INSIDER]))
    (i,) = client.companies.insiders("AAPL")
    check_insider(i)


@respx.mock
def test_insiders_search_ignores_unknown_fields(client):
    respx.get(f"{BASE}/v1/insiders").mock(return_value=httpx.Response(200, json=[INSIDER]))
    (i,) = client.insiders.search("cook")
    check_insider(i)


@respx.mock
def test_insiders_get_ignores_unknown_fields(client):
    respx.get(f"{BASE}/v1/insiders/0001214156").mock(return_value=httpx.Response(200, json=INSIDER))
    check_insider(client.insiders.get("0001214156"))


@respx.mock
def test_signals_list_ignores_unknown_fields(client):
    respx.get(f"{BASE}/v1/signals").mock(return_value=httpx.Response(200, json=[SIGNAL]))
    (s,) = client.signals.list()
    check_signal(s)


@respx.mock
def test_signals_paginate_ignores_unknown_fields(client):
    respx.get(f"{BASE}/v1/signals").mock(return_value=httpx.Response(200, json=[SIGNAL]))
    (page,) = list(client.signals.paginate(per_page=100, max_pages=1))
    (s,) = page
    check_signal(s)


@respx.mock
def test_webhooks_create_ignores_unknown_fields(client):
    respx.post(f"{BASE}/v1/webhooks").mock(return_value=httpx.Response(201, json=WH_CREATED))
    check_created(client.webhooks.create("https://example.com/hook", ["Form4Filed"]))


@respx.mock
def test_webhooks_list_ignores_unknown_fields(client):
    respx.get(f"{BASE}/v1/webhooks").mock(return_value=httpx.Response(200, json=[WH_SUB]))
    (w,) = client.webhooks.list()
    check_sub(w)


@respx.mock
def test_webhooks_events_ignores_unknown_fields(client):
    respx.get(f"{BASE}/v1/webhooks/events").mock(return_value=httpx.Response(200, json=[WH_EVENT]))
    (e,) = client.webhooks.events()
    check_event(e)


# ── async ────────────────────────────────────────────────────────────────────

@respx.mock
def test_async_companies_get_ignores_unknown_fields():
    respx.get(f"{BASE}/v1/companies/AAPL").mock(return_value=httpx.Response(200, json=COMPANY))
    check_company(run_async(lambda c: c.companies.get("AAPL")))


@respx.mock
def test_async_companies_insiders_ignores_unknown_fields():
    respx.get(f"{BASE}/v1/companies/AAPL/insiders").mock(return_value=httpx.Response(200, json=[INSIDER]))
    (i,) = run_async(lambda c: c.companies.insiders("AAPL"))
    check_insider(i)


@respx.mock
def test_async_insiders_search_ignores_unknown_fields():
    respx.get(f"{BASE}/v1/insiders").mock(return_value=httpx.Response(200, json=[INSIDER]))
    (i,) = run_async(lambda c: c.insiders.search("cook"))
    check_insider(i)


@respx.mock
def test_async_insiders_get_ignores_unknown_fields():
    respx.get(f"{BASE}/v1/insiders/0001214156").mock(return_value=httpx.Response(200, json=INSIDER))
    check_insider(run_async(lambda c: c.insiders.get("0001214156")))


@respx.mock
def test_async_signals_list_ignores_unknown_fields():
    respx.get(f"{BASE}/v1/signals").mock(return_value=httpx.Response(200, json=[SIGNAL]))
    (s,) = run_async(lambda c: c.signals.list())
    check_signal(s)


@respx.mock
def test_async_signals_paginate_ignores_unknown_fields():
    respx.get(f"{BASE}/v1/signals").mock(return_value=httpx.Response(200, json=[SIGNAL]))

    async def go(c):
        return [s async for s in c.signals.paginate(per_page=100, max_pages=1)]

    (page,) = run_async(go)
    (s,) = page
    check_signal(s)


@respx.mock
def test_async_webhooks_create_ignores_unknown_fields():
    respx.post(f"{BASE}/v1/webhooks").mock(return_value=httpx.Response(201, json=WH_CREATED))
    check_created(run_async(lambda c: c.webhooks.create("https://example.com/hook", ["Form4Filed"])))


@respx.mock
def test_async_webhooks_list_ignores_unknown_fields():
    respx.get(f"{BASE}/v1/webhooks").mock(return_value=httpx.Response(200, json=[WH_SUB]))
    (w,) = run_async(lambda c: c.webhooks.list())
    check_sub(w)


@respx.mock
def test_async_webhooks_events_ignores_unknown_fields():
    respx.get(f"{BASE}/v1/webhooks/events").mock(return_value=httpx.Response(200, json=[WH_EVENT]))
    (e,) = run_async(lambda c: c.webhooks.events())
    check_event(e)
