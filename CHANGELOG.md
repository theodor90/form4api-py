# Changelog

## Unreleased

## 0.11.0 — 2026-10-13

- **`webhooks.update(id, url)` (sync and async).** Changes the delivery URL of
  a webhook subscription (`PATCH /v1/webhooks/{id}`) and returns the updated
  `WebhookSubscription`. The id, secret, event types and auth header are kept.
  The URL is checked the same way as on create (HTTPS, public address, at most
  500 characters); a rejected URL raises `Form4ApiError` with the code in
  `error_code` (`INVALID_REQUEST`, `INVALID_URL`, `INSECURE_URL`,
  `PRIVATE_ADDRESS` or `UNRESOLVABLE_HOST`). It works on disabled
  subscriptions but does not re-enable them, so call `enable(id)` afterwards.
  The `last_*` health fields come back `None`. Available on every plan.
- **`url_warning`.** `WebhookSubscription` and `WebhookCreated` gain
  `url_warning`: a string when the URL's host is a temporary tunnel or test host
  (trycloudflare, ngrok, webhook.site, loca.lt, serveo), otherwise `None`. It is
  a warning only. Older payloads without the field still parse (default `None`).
- `webhooks.create()` now gets a 400 `INVALID_URL` for URLs over 500
  characters (API change).

## 0.10.0 — 2026-10-13

- **Webhooks (sync and async).** New methods: `webhooks.enable(id)` (re-enable
  a subscription the system auto-disabled), `webhooks.test(id)` (send one
  synthetic delivery; a failed send comes back as `delivered=False` with an
  `error`, it does not raise), `webhooks.set_auth_header(id, name, value)` and
  `webhooks.delete_auth_header(id)` (returns `None` on 204). `webhooks.create()`
  takes an optional `auth_header={"name": ..., "value": ...}` that is sent with
  every delivery. `WebhookSubscription` gains `is_read_only`, `disabled_at`,
  `disabled_reason`, `last_attempt_at`, `last_success_at`, `last_status_code`,
  `last_error_class` and `auth_header_name`; `WebhookCreated` gains
  `is_read_only` and `auth_header_name`. All default to `None`. The auth header
  value is write-only and never returned.
- **Schedule 13D/13G.** New `client.ownership.schedule_13dg()` for
  `GET /v1/ownership/13d-13g` (Business plan), sync and async. The endpoint
  existed in the API but had no method because the `Ownership` tag was missing
  from the generator.
- **`transactions.list()` / `paginate()` filters (sync and async).** Added
  `min_return_1d/1w/1m/3m/6m`, `max_return_1d/1w/1m/3m/6m`, `has_returns` (all
  Pro+), `inst_ownership_trend` (`"increasing"`, `"decreasing"` or `"stable"`),
  `role` (`"officer"`, `"director"` or `"ten_percent_owner"`) and `sort`
  (`"date"` or `"value"`). Returns are fractions (0.2 = +20%).
- `Transaction` gains `filed_at` (when the filing became public on EDGAR).
- `verify_webhook()` now returns `False` instead of raising `TypeError` when the
  signature header is missing or contains non-ASCII characters.
- README: documented `verify_webhook`, the webhook methods and all five event
  types, fixed `client.status.history()` (it takes no parameters), and fixed the
  `min_value` note (available on every plan; `max_value`, `min_shares`,
  `max_shares` and the return filters are Pro+).
- Regenerated `form4api/_generated.py` from the live spec (new
  `GeneratedOwnershipResource`, `WebhookAuthHeaderRequest`, `filed_at` on
  `TransactionResponse`; some endpoint descriptions updated).
- Added `form4api.__version__` (read from the installed package metadata, so it
  always equals the pyproject version).
- Responses with fields added by newer API versions no longer raise
  `TypeError` in companies/insiders/signals/webhooks methods (sync and async).
  Unknown keys are now ignored, as the transactions, search and generated
  models already did.

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
