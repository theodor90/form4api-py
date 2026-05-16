# form4api

Python client for [Form4API](https://form4api.com) — real-time SEC Form 4 insider trading data.

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
| `client.insiders` | `.search(name, **params)`, `.get(cik)`, `.transactions(cik, **params)` |
| `client.companies` | `.get(ticker)`, `.insiders(ticker)` |
| `client.signals` | `.list(**params)`, `.paginate(**params)` — Business plan |
| `client.webhooks` | `.create(url, event_types)`, `.list()`, `.delete(id)`, `.events(**params)` |

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
for batch in client.transactions.paginate(ticker="NVDA", exclude_10b5=True, per_page=500):
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
