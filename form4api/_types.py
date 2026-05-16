from __future__ import annotations

from dataclasses import dataclass


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


@dataclass
class Insider:
    cik: str
    name: str
    is_director: bool
    is_officer: bool
    is_ten_percent_owner: bool
    officer_title: str | None
    total_filings: int


@dataclass
class Company:
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
class InsiderSignal:
    ticker: str | None
    company_name: str
    signal_date: str
    buy_sell_ratio: float
    is_cluster_buy: bool
    is_cluster_sell: bool
    insider_count: int


@dataclass
class WebhookCreated:
    subscription_id: int
    url: str
    event_types: list[str]
    secret: str
    created_at: str
    warning: str | None


@dataclass
class WebhookSubscription:
    subscription_id: int
    url: str
    event_types: list[str]
    created_at: str
    is_active: bool


@dataclass
class WebhookEvent:
    delivery_id: int
    subscription_id: int
    event_type: str
    attempt_count: int
    delivered_at: str | None
    next_retry_at: str | None
    last_status_code: int | None
    is_dead: bool
    payload: str



