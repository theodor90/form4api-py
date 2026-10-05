from __future__ import annotations

from dataclasses import dataclass, fields


class _FromDictMixin:
    """Tolerant construction for flat dataclasses built from API payloads.

    The API only ever adds fields, and a dataclass constructor rejects unknown
    keyword arguments, so `Model(**data)` crashes on the first new field.
    `_from_dict` drops keys the dataclass does not declare. Key conversion
    (camelCase to snake_case) already happened in the client before this runs.
    Models with nested dataclasses override `_from_dict` to hydrate them."""

    @classmethod
    def _from_dict(cls, data: dict):
        known = {f.name for f in fields(cls)}  # type: ignore[arg-type]
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class TopHolder:
    manager_cik: str | None = None
    manager_name: str | None = None
    shares: float | None = None
    value: float | None = None

    @classmethod
    def _from_dict(cls, data: dict) -> "TopHolder":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class InstitutionalOwnership:
    quarter: str | None = None
    total_aum_usd: float | None = None
    delta_qoq_pct: float | None = None
    trend: str | None = None
    top_holders: list[TopHolder] | None = None
    coverage_incomplete: bool | None = None

    @classmethod
    def _from_dict(cls, data: dict) -> "InstitutionalOwnership":
        known = {f.name for f in fields(cls)}
        kwargs = {k: v for k, v in data.items() if k in known}
        if isinstance(kwargs.get("top_holders"), list):
            kwargs["top_holders"] = [
                TopHolder._from_dict(i) if isinstance(i, dict) else i for i in kwargs["top_holders"]
            ]
        return cls(**kwargs)


@dataclass
class Transaction:
    ticker: str
    company_name: str
    insider_name: str
    insider_cik: str
    insider_title: str | None
    is_director: bool
    is_officer: bool
    is10_pct_owner: bool
    accession_number: str
    security_title: str
    transaction_code: str
    is_open_market: bool
    is10b5_plan: bool
    shares_amount: float
    price_per_share: float | None
    total_value: float | None
    shares_owned_after: float | None
    direct_indirect: str | None
    is_derivative: bool
    transaction_date: str
    period_of_report: str
    # Added 2026-09-24: return columns, source-quality flag, SEC acceptance
    # timestamp, and the public document URL. All optional so an older SDK
    # keeps working against a payload that doesn't send them, and a newer
    # backend can add more without breaking this dataclass's constructor.
    return1d: float | None = None
    return1w: float | None = None
    return1m: float | None = None
    return3m: float | None = None
    return6m: float | None = None
    value_quality: str | None = None
    accepted_at: str | None = None
    document_url: str | None = None
    institutional_ownership: InstitutionalOwnership | None = None

    @classmethod
    def _from_dict(cls, data: dict) -> "Transaction":
        """Build from an API payload, ignoring unknown keys and hydrating the
        nested `institutional_ownership` object instead of leaving it a raw
        dict (see codegen/generate.py for the history of that bug)."""
        known = {f.name for f in fields(cls)}
        kwargs = {k: v for k, v in data.items() if k in known}
        if isinstance(kwargs.get("institutional_ownership"), dict):
            kwargs["institutional_ownership"] = InstitutionalOwnership._from_dict(
                kwargs["institutional_ownership"]
            )
        return cls(**kwargs)


@dataclass
class Insider(_FromDictMixin):
    cik: str
    name: str
    is_director: bool
    is_officer: bool
    is_ten_percent_owner: bool
    officer_title: str | None
    total_filings: int


@dataclass
class Company(_FromDictMixin):
    cik: str
    name: str
    ticker: str | None
    exchange: str | None
    total_filings: int
    active_insiders: int
    sic_description: str | None
    state_of_incorporation: str | None
    website: str | None


@dataclass
class SearchCompany:
    ticker: str
    name: str
    cik: str

    @classmethod
    def _from_dict(cls, data: dict) -> "SearchCompany":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class SearchInsider:
    cik: str
    name: str
    title: str | None
    # A ticker associated with the insider (may be None).
    ticker: str | None

    @classmethod
    def _from_dict(cls, data: dict) -> "SearchInsider":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class SearchResults:
    companies: list[SearchCompany]
    insiders: list[SearchInsider]

    @classmethod
    def _from_dict(cls, data: dict) -> "SearchResults":
        """Build from the `/v1/search` payload, hydrating both arrays into
        their own dataclasses rather than leaving them as raw dicts (see
        Transaction._from_dict for why filtering unknown keys matters here
        too — a field the backend adds later must not crash an older SDK)."""
        return cls(
            companies=[SearchCompany._from_dict(c) for c in (data.get("companies") or [])],
            insiders=[SearchInsider._from_dict(i) for i in (data.get("insiders") or [])],
        )


@dataclass
class InsiderSignal(_FromDictMixin):
    ticker: str | None
    company_name: str
    signal_date: str
    buy_sell_ratio: float
    is_cluster_buy: bool
    is_cluster_sell: bool
    insider_count: int


@dataclass
class WebhookCreated(_FromDictMixin):
    subscription_id: int
    url: str
    event_types: list[str]
    secret: str
    created_at: str
    warning: str | None


@dataclass
class WebhookSubscription(_FromDictMixin):
    subscription_id: int
    url: str
    event_types: list[str]
    created_at: str
    is_active: bool


@dataclass
class WebhookEvent(_FromDictMixin):
    delivery_id: int
    subscription_id: int
    event_type: str
    attempt_count: int
    delivered_at: str | None
    next_retry_at: str | None
    last_status_code: int | None
    is_dead: bool
    payload: str



