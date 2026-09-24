# Changelog

## 0.8.0 — 2026-09-24

- **Fixed:** `transactions.list()`, `transactions.paginate()` and
  `insiders.transactions()` raised `TypeError: unexpected keyword argument
  'return1d'` on real API responses, because the API returns fields the
  `Transaction` dataclass did not declare. Transactions are now built with
  `Transaction._from_dict()`, which also ignores any field added to the API
  in future instead of failing.
- `transactions.list()` and `transactions.paginate()` accept `filed_from`/
  `filed_to` to filter on the date a filing hit EDGAR, separate from the
  existing `from_date`/`to_date` (which filter on the transaction's own
  reported date).
- `ticker` on `transactions.list()`/`paginate()` accepts up to 25
  comma-separated symbols, e.g. `ticker="AAPL,MSFT,NVDA"`.
- `Transaction` gained `return1d`/`return1w`/`return1m`/`return3m`/`return6m`,
  `value_quality`, `accepted_at`, `document_url`, and
  `institutional_ownership` (a new `InstitutionalOwnership`/`TopHolder` pair
  of dataclasses, hydrated as objects, not dicts) — all optional, so older
  payloads without them still parse.
- `limit` is now accepted as an alias for `per_page` on the codegen'd list
  endpoints (`per_page` still wins if both are sent) — picked up automatically
  by regenerating from the OpenAPI spec.
- `FilingResponse` gained `accepted_at`/`document_url`; `Form144Response`
  gained `filer_cik`/`securities_class_title`/`document_url` — both
  spec-derived, no code changes needed beyond regenerating.
- Regenerated `form4api/_generated.py` from the current OpenAPI spec.

## Earlier versions

Not tracked in this file — see PyPI release history.
