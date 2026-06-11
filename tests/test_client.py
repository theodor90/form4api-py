import pytest
import httpx
import respx

from form4api import (
    Form4ApiClient,
    AuthError,
    NotFoundError,
    PlanError,
    RateLimitError,
    Form4ApiError,
    Transaction,
    Insider,
    Company,
    InsiderSignal,
    verify_webhook,
)

BASE = "https://api.form4api.com"

TX = {
    "ticker": "AAPL",
    "companyName": "Apple Inc.",
    "insiderName": "Cook Timothy D",
    "insiderCik": "0001214156",
    "insiderTitle": "Chief Executive Officer",
    "isDirector": False,
    "isOfficer": True,
    "is10PctOwner": False,
    "accessionNumber": "0001234567-26-000001",
    "securityTitle": "Common Stock",
    "transactionCode": "P",
    "isOpenMarket": True,
    "is10b5Plan": False,
    "sharesAmount": 1000.0,
    "pricePerShare": 212.45,
    "totalValue": 212450.0,
    "sharesOwnedAfter": 5000.0,
    "directIndirect": "D",
    "isDerivative": False,
    "transactionDate": "2026-01-15T00:00:00Z",
    "periodOfReport": "2026-01-15T00:00:00Z",
}

INSIDER = {
    "cik": "0001214156",
    "name": "Cook Timothy D",
    "isDirector": False,
    "isOfficer": True,
    "isTenPercentOwner": False,
    "officerTitle": "CEO",
    "totalFilings": 42,
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
}

SIGNAL = {
    "ticker": "AAPL",
    "companyName": "Apple Inc.",
    "signalDate": "2026-01-15",
    "buySellRatio": 2.5,
    "isClusterBuy": True,
    "isClusterSell": False,
    "insiderCount": 4,
}


@pytest.fixture
def client():
    with Form4ApiClient("test-key", max_retries=0) as c:
        yield c


# ── transactions ───────────────────────────────────────────────────────────────

@respx.mock
def test_transactions_list_returns_typed_objects(client):
    respx.get(f"{BASE}/v1/transactions").mock(return_value=httpx.Response(200, json=[TX]))
    results = client.transactions.list()
    assert len(results) == 1
    assert isinstance(results[0], Transaction)
    assert results[0].ticker == "AAPL"
    assert results[0].company_name == "Apple Inc."
    assert results[0].insider_cik == "0001214156"
    assert results[0].transaction_code == "P"


@respx.mock
def test_transactions_list_sends_filters(client):
    route = respx.get(f"{BASE}/v1/transactions").mock(return_value=httpx.Response(200, json=[]))
    client.transactions.list(ticker="AAPL", code="P", from_date="2026-01-01", per_page=10)
    assert route.called
    qs = dict(route.calls[0].request.url.params)
    assert qs["ticker"] == "AAPL"
    assert qs["code"] == "P"
    assert qs["from"] == "2026-01-01"
    assert qs["per_page"] == "10"


@respx.mock
def test_transactions_list_sends_granular_filters(client):
    route = respx.get(f"{BASE}/v1/transactions").mock(return_value=httpx.Response(200, json=[]))
    client.transactions.list(
        codes="P,S",
        exclude_codes="A,M",
        category="open_market",
        exclude_category="derivatives",
        exclude_derivative=True,
        significant=True,
        min_value=100000,
        max_value=5000000,
        min_shares=100,
        max_shares=10000,
    )
    assert route.called
    qs = dict(route.calls[0].request.url.params)
    assert qs["codes"] == "P,S"
    assert qs["exclude_codes"] == "A,M"
    assert qs["category"] == "open_market"
    assert qs["exclude_category"] == "derivatives"
    assert qs["exclude_derivative"] == "true"
    assert qs["significant"] == "true"
    assert qs["min_value"] == "100000"
    assert qs["max_value"] == "5000000"
    assert qs["min_shares"] == "100"
    assert qs["max_shares"] == "10000"


@respx.mock
def test_transactions_paginate_stops_on_short_page(client):
    respx.get(f"{BASE}/v1/transactions").mock(side_effect=[
        httpx.Response(200, json=[TX]),
        httpx.Response(200, json=[]),
    ])
    pages = list(client.transactions.paginate(per_page=1))
    assert len(pages) == 1
    assert pages[0][0].ticker == "AAPL"


# ── insiders ──────────────────────────────────────────────────────────────────

@respx.mock
def test_insiders_search_returns_list(client):
    route = respx.get(f"{BASE}/v1/insiders").mock(return_value=httpx.Response(200, json=[INSIDER]))
    results = client.insiders.search("Cook")
    assert route.called
    qs = dict(route.calls[0].request.url.params)
    assert qs["name"] == "Cook"
    assert len(results) == 1
    assert isinstance(results[0], Insider)
    assert results[0].name == "Cook Timothy D"


@respx.mock
def test_insiders_get_returns_typed_object(client):
    respx.get(f"{BASE}/v1/insiders/0001214156").mock(return_value=httpx.Response(200, json=INSIDER))
    result = client.insiders.get("0001214156")
    assert isinstance(result, Insider)
    assert result.cik == "0001214156"
    assert result.is_officer is True
    assert result.total_filings == 42


@respx.mock
def test_insiders_transactions_returns_list(client):
    respx.get(f"{BASE}/v1/insiders/0001214156/transactions").mock(
        return_value=httpx.Response(200, json=[TX])
    )
    results = client.insiders.transactions("0001214156")
    assert len(results) == 1
    assert isinstance(results[0], Transaction)


# ── companies ─────────────────────────────────────────────────────────────────

@respx.mock
def test_companies_get_returns_typed_object(client):
    respx.get(f"{BASE}/v1/companies/AAPL").mock(return_value=httpx.Response(200, json=COMPANY))
    result = client.companies.get("AAPL")
    assert isinstance(result, Company)
    assert result.ticker == "AAPL"
    assert result.total_filings == 100
    assert result.active_insiders == 12


@respx.mock
def test_companies_insiders_returns_list(client):
    respx.get(f"{BASE}/v1/companies/AAPL/insiders").mock(
        return_value=httpx.Response(200, json=[INSIDER])
    )
    results = client.companies.insiders("AAPL")
    assert len(results) == 1
    assert isinstance(results[0], Insider)


# ── signals ───────────────────────────────────────────────────────────────────

@respx.mock
def test_signals_list_returns_typed_objects(client):
    respx.get(f"{BASE}/v1/signals").mock(return_value=httpx.Response(200, json=[SIGNAL]))
    results = client.signals.list(ticker="AAPL")
    assert len(results) == 1
    assert isinstance(results[0], InsiderSignal)
    assert results[0].is_cluster_buy is True
    assert results[0].buy_sell_ratio == 2.5


# ── error handling ────────────────────────────────────────────────────────────

@respx.mock
def test_401_raises_auth_error(client):
    respx.get(f"{BASE}/v1/transactions").mock(
        return_value=httpx.Response(401, json={"error": {"code": "INVALID_API_KEY", "message": "Bad key"}})
    )
    with pytest.raises(AuthError) as exc:
        client.transactions.list()
    assert exc.value.status_code == 401
    assert exc.value.error_code == "INVALID_API_KEY"


@respx.mock
def test_402_raises_plan_error(client):
    respx.get(f"{BASE}/v1/signals").mock(
        return_value=httpx.Response(402, json={"error": {"code": "PLAN_REQUIRED", "message": "Upgrade"}, "requiredPlan": "Business"})
    )
    with pytest.raises(PlanError) as exc:
        client.signals.list()
    assert exc.value.required_plan == "Business"


@respx.mock
def test_404_raises_not_found_error(client):
    respx.get(f"{BASE}/v1/insiders/0000000000").mock(
        return_value=httpx.Response(404, json={"error": {"code": "NOT_FOUND", "message": "Not found"}})
    )
    with pytest.raises(NotFoundError):
        client.insiders.get("0000000000")


@respx.mock
def test_429_raises_rate_limit_error_with_retry_after(client):
    respx.get(f"{BASE}/v1/transactions").mock(
        return_value=httpx.Response(
            429,
            headers={"Retry-After": "42"},
            json={"error": {"code": "RATE_LIMIT_EXCEEDED", "message": "Slow down"}},
        )
    )
    with pytest.raises(RateLimitError) as exc:
        client.transactions.list()
    assert exc.value.retry_after == 42


@respx.mock
def test_500_raises_form4_api_error(client):
    respx.get(f"{BASE}/v1/transactions").mock(return_value=httpx.Response(500, json={}))
    with pytest.raises(Form4ApiError) as exc:
        client.transactions.list()
    assert exc.value.status_code == 500


# ── retries ───────────────────────────────────────────────────────────────────

@respx.mock
def test_retries_on_5xx_then_succeeds():
    with Form4ApiClient("test-key", max_retries=1) as client:
        respx.get(f"{BASE}/v1/transactions").mock(side_effect=[
            httpx.Response(503, json={}),
            httpx.Response(200, json=[TX]),
        ])
        results = client.transactions.list()
    assert len(results) == 1


@respx.mock
def test_no_retry_on_4xx():
    call_count = 0

    def handler(_):
        nonlocal call_count
        call_count += 1
        return httpx.Response(401, json={"error": {"code": "INVALID_API_KEY", "message": "Bad"}})

    with Form4ApiClient("test-key", max_retries=2) as client:
        respx.get(f"{BASE}/v1/transactions").mock(side_effect=handler)
        with pytest.raises(AuthError):
            client.transactions.list()

    assert call_count == 1  # no retries on 401


# ── webhook verification ──────────────────────────────────────────────────────

def test_verify_webhook_valid_signature():
    import hashlib, hmac as _hmac
    payload = b'{"type":"TransactionFiled"}'
    secret = "mysecret"
    sig = "sha256=" + _hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    assert verify_webhook(payload, sig, secret) is True


def test_verify_webhook_invalid_signature():
    assert verify_webhook(b"payload", "sha256=badhash", "mysecret") is False


def test_verify_webhook_accepts_str_payload():
    import hashlib, hmac as _hmac
    payload = '{"type":"TransactionFiled"}'
    secret = "mysecret"
    sig = "sha256=" + _hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    assert verify_webhook(payload, sig, secret) is True
