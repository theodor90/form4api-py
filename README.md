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

# Recent open-market purchases at Apple
txns = client.transactions.list(ticker="AAPL", code="P", per_page=5)
for t in txns:
    print(t.insider_name, t.shares_amount, "@", t.price_per_share)

# Company overview
company = client.companies.get("MSFT")
print(company.name, company.active_insiders, "active insiders")

# Insider detail
insider = client.insiders.get("0001234567")
print(insider.name, insider.officer_title)

# Cluster-buy signals (Business plan)
signals = client.signals.list(ticker="NVDA")
for sig in signals:
    if sig.is_cluster_buy:
        print(sig.company_name, sig.insider_count, "buyers")
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
| `client.signals` | `.list(**params)` — Business plan |
| `client.webhooks` | `.create(url, event_types)`, `.list()`, `.delete(id)`, `.events(**params)` |

## Error handling

```python
from form4api import Form4ApiClient, AuthError, PlanError, RateLimitError, NotFoundError

client = Form4ApiClient("YOUR_API_KEY")

try:
    signals = client.signals.list()
except PlanError as e:
    print(f"Upgrade to {e.required_plan}")
except RateLimitError as e:
    print(f"Retry after {e.retry_after}s")
except AuthError:
    print("Invalid API key")
except NotFoundError:
    print("Resource not found")
```

## License

MIT
