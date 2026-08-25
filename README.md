# form4api

Python client for [Form4API](https://www.form4api.com) — real-time SEC Form 4 insider trading data.

[![PyPI version](https://img.shields.io/pypi/v/form4api.svg)](https://pypi.org/project/form4api/)
[![PyPI downloads](https://img.shields.io/pypi/dm/form4api.svg)](https://pypi.org/project/form4api/)
[![Python versions](https://img.shields.io/pypi/pyversions/form4api.svg)](https://pypi.org/project/form4api/)
[![license](https://img.shields.io/pypi/l/form4api.svg)](https://github.com/theodor90/form4api-py/blob/main/LICENSE)

Supports Python 3.11+. Uses `httpx` for both sync and async HTTP.

## Installation

```bash
pip install form4api
```

## Sync quickstart

```python
from form4api import Form4ApiClient

client = Form4ApiClient("YOUR_API_KEY")

# Recent open-market purchases at Apple (excluding 10b5-1 plan trades)
txns = client.transactions.list(ticker="AAPL", code="P", exclude_10b5=True, per_page=5)
for t in txns:
    print(t.insider_name, t.insider_title, t.shares_amount, "@", t.price_per_share)
    print(f"  open market: {t.is_open_market}, 10b5 plan: {t.is10b5_plan}, value: ${t.total_value:,.0f}")

# Company overview (includes SIC, state, website)
company = client.companies.get("MSFT")
print(company.name, company.active_insiders, "active insiders")
print(company.sic_description, company.state_of_incorporation)

# Insider detail
insider = client.insiders.get("0001234567")
print(insider.name, insider.officer_title)

# Cluster-buy signals (Business plan)
signals = client.signals.list(cluster_buy=True)
for sig in signals:
    print(sig.company_name, sig.insider_count, "buyers on", sig.signal_date)
```

## Async quickstart

```python
import asyncio
from form4api import AsyncForm4ApiClient

async def main():
    async with AsyncForm4ApiClient("YOUR_API_KEY") as client:
        txns = await client.transactions.list(ticker="AAPL", per_page=5)
        for t in txns:
            print(t.insider_name, t.shares_amount, "@", t.price_per_share)

asyncio.run(main())
```

## Resources

| Resource | Methods |
|---|---|
| `client.transactions` | `.list(**params)`, `.paginate(**params)` |
| `client.insiders` | `.search(name, **params)`, `.get(cik)`, `.list(**params)`, `.directory(**params)`, `.transactions(cik, **params)`, `.summary(cik)` *(Pro)*, `.scorecard(cik)` *(Pro)*, `.leaderboard(**params)` *(Business)* |
| `client.companies` | `.get(ticker)`, `.insiders(ticker)`, `.list(**params)` |
| `client.signals` | `.list(**params)`, `.paginate(**params)`, `.explain(ticker)`, `.sentiment(ticker, **params)` — Business; `.convergence(**params)` — Pro |
| `client.congress` | `.trades(**params)`, `.politicians(**params)` *(Pro)*, `.politician(id_or_slug)` *(Pro)*, `.ticker(ticker)` *(Pro)* |
| `client.form144` | `.list(**params)` — Business plan |
| `client.holdings` | `.list(**params)`, `.managers(**params)` — Business plan |
| `client.filings` | `.list(**params)`, `.recent(**params)`, `.get(accession_number)` |
| `client.stats` | `.get()` — public, no key required |
| `client.data_quality` | `.get()` — public, no key required |
| `client.status` | `.history(**params)` |
| `client.webhooks` | `.create(url, event_types)`, `.list()`, `.delete(id)`, `.events(**params)` |

Every plan-gated endpoint the API exposes has a typed method here. Calling one
your key isn't entitled to raises `PlanError` (HTTP 402) carrying
`required_plan`, `current_plan`, and `upgrade_url` rather than failing opaquely.

An `AsyncForm4ApiClient` mirrors the whole surface with the same resources and
method names — `await client.insiders.leaderboard()`.

For the full parameter reference see the [REST docs](https://form4api.com/docs).
For LLM workflows, `form4api-mcp` exposes the same endpoints as tools.

### Transaction filters

```python
client.transactions.list(
    ticker="AAPL",        # filter by ticker
    cik="0000320193",     # or by company CIK
    insider_cik="...",    # filter by insider CIK
    code="P",             # transaction code: P=purchase, S=sale, A=grant, etc.
    from_date="2026-01-01",
    to_date="2026-12-31",
    exclude_10b5=True,    # omit trades filed under a Rule 10b5-1 plan
    per_page=100,
    page=1,
)
```

### Granular filtering (v0.4.0+)

```python
# The "just show me real buys & sells" preset: open-market only,
# no 10b5-1 plan trades, no derivatives.
client.transactions.list(ticker="AAPL", significant=True)

# Multi-code include / exclude (comma-separated SEC codes)
client.transactions.list(codes="P,S")
client.transactions.list(exclude_codes="A,M,F,G")

# Whole-category filters: open_market | grants | derivatives | gifts | other
client.transactions.list(category="open_market")
client.transactions.list(exclude_category="derivatives")
client.transactions.list(exclude_derivative=True)

# Trade-size screening (Pro plan or higher)
client.transactions.list(min_value=1_000_000)          # USD, shares x price
client.transactions.list(min_shares=10_000, max_shares=100_000)
```

### Transaction fields

| Field | Type | Description |
|-------|------|-------------|
| `ticker` | `str` | Stock ticker |
| `company_name` | `str` | Company name |
| `insider_name` | `str` | Insider full name |
| `insider_cik` | `str` | Insider CIK |
| `insider_title` | `str \| None` | Officer title as reported on the Form 4 |
| `is_director` | `bool` | Director flag |
| `is_officer` | `bool` | Officer flag |
| `is10_pct_owner` | `bool` | 10% owner flag |
| `accession_number` | `str` | SEC accession number |
| `security_title` | `str` | Security type |
| `transaction_code` | `str` | Transaction code |
| `is_open_market` | `bool` | `True` when code is P or S (not grants/awards) |
| `is10b5_plan` | `bool` | Filed under a Rule 10b5-1 pre-scheduled trading plan |
| `shares_amount` | `float` | Shares transacted |
| `price_per_share` | `float \| None` | Price per share |
| `total_value` | `float \| None` | `shares_amount × price_per_share` in USD |
| `shares_owned_after` | `float \| None` | Holdings after transaction |
| `direct_indirect` | `str \| None` | "D" (direct) or "I" (indirect) |
| `is_derivative` | `bool` | Derivative security flag |
| `transaction_date` | `str` | ISO datetime |
| `period_of_report` | `str` | ISO datetime |

### Company fields

| Field | Type | Description |
|-------|------|-------------|
| `cik` | `str` | SEC CIK |
| `name` | `str` | Company name |
| `ticker` | `str \| None` | Stock ticker |
| `exchange` | `str \| None` | Exchange |
| `total_filings` | `int` | Total Form 4 filings |
| `active_insiders` | `int` | Distinct insiders who have filed |
| `sic_description` | `str \| None` | SEC SIC industry description |
| `state_of_incorporation` | `str \| None` | Two-letter state code |
| `website` | `str \| None` | Company website as filed with SEC |

### Pagination

```python
# transactions.paginate() — yields one list per page automatically
all_txns = []
for batch in client.transactions.paginate(ticker="NVDA", exclude_10b5=True, per_page=100):
    all_txns.extend(batch)

# signals.paginate()
all_signals = []
for batch in client.signals.paginate(cluster_buy=True, per_page=100):
    all_signals.extend(batch)
```

## Error handling

```python
from form4api import Form4ApiClient, AuthError, PlanError, RateLimitError, NotFoundError

client = Form4ApiClient("YOUR_API_KEY")

try:
    signals = client.signals.list()
except PlanError as e:
    print(f"Upgrade required")
except RateLimitError as e:
    print(f"Retry after {e.retry_after}s")
except AuthError:
    print("Invalid API key")
except NotFoundError:
    print("Resource not found")
```

## License

MIT
