# Changelog

## Unreleased

## 0.9.0 — 2026-10-05

- **Congress date quality (backend insiderapi #330/#331).** `CongressTradeDto`
  and `ConvergenceCongressLegDto` gained `date_quality: str | None`.
  `disclosure_lag_days` was already `int | None` in these models (every
  generated field is optional), so its type is unchanged, but it can now
  actually be `None`: when the filing's own dates are impossible or
  implausible the lag is `None` and `date_quality` names the reason
  (`"transaction_after_disclosure"`, `"future_transaction_date"` or
  `"implausible_lag"`; a free-form string in the spec, not an enum). A `None`
  lag with a code means the filing's own dates are impossible; the raw
  `transaction_date` and `disclosure_date` are still returned and flagged rows
  are never dropped. On convergence legs `date_quality` is always `None` in
  practice (flagged trades are excluded from convergence). A lag over 45 days
  is not a legal finding. Code that does arithmetic on `disclosure_lag_days`
  needs a `None` check. Webhook payloads (`CongressTradeFiled`,
  `ConvergenceSignal`) carry the same two fields in PascalCase; this SDK has no
  webhook payload models, so nothing to change there.
- Regenerated `form4api/_generated.py` from the live spec: the
  `congress.trades()` and `signals.convergence()` docstrings (sync and async)
  pick up the new descriptions, and the spec's `SearchCompanyResult` /
  `SearchInsiderResult` / `SearchResponse` response dataclasses are now
  emitted too. They are not exported; `client.search()` keeps returning the
  hand-written `SearchResults`.

Also in this release (previously unreleased):

- Added `client.search(q, limit=None)` (sync and async) for the new
  `GET /v1/search` endpoint — a combined company + insider lookup by name or
  ticker, returning typed `SearchResults` (`companies: list[SearchCompany]`,
  `insiders: list[SearchInsider]`). `q` must be 2-64 characters; the API's
  `QUERY_TOO_SHORT`/`QUERY_TOO_LONG` 400s surface as `Form4ApiError`.

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
