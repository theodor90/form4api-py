"""Smoke test for the INSTALLED form4api wheel.

Run by scripts/release_check.py with the temp venv's python, in isolated mode
(-I) and with a working directory outside the repo, so the source tree cannot
be imported by accident. Needs no network and no API key.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import pkgutil
import sys
import typing
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expected-version", required=True)
    ap.add_argument("--forbid-root", required=True, help="the repo root; importing from under it is a failure")
    args = ap.parse_args()

    import form4api

    loc = Path(form4api.__file__).resolve()
    assert Path(args.forbid_root).resolve() not in loc.parents, f"form4api imported from the source tree: {loc}"
    print(f"  form4api imported from {loc.parent}")

    # 1. every module imports (public and private: a missing dependency or a
    # syntax error in any of them breaks users on first use).
    failures: list[str] = []
    names = [m.name for m in pkgutil.walk_packages(form4api.__path__, "form4api.", onerror=lambda n: failures.append(n))]
    assert not failures, f"packages that failed to walk: {failures}"
    for name in names:
        importlib.import_module(name)
    print(f"  imported {len(names)} submodules: {', '.join(n.removeprefix('form4api.') for n in names)}")
    for export in form4api.__all__:
        assert hasattr(form4api, export), f"__all__ lists {export!r} but it does not resolve"
    print(f"  all {len(form4api.__all__)} names in __all__ resolve")

    # 2. version
    assert form4api.__version__ == args.expected_version, (
        f"form4api.__version__ is {form4api.__version__!r}, pyproject says {args.expected_version!r}"
    )
    from importlib.metadata import version

    assert version("form4api") == args.expected_version, "installed distribution metadata disagrees"
    print(f"  __version__ == {form4api.__version__}")

    # 3. construct both clients
    client = form4api.Form4ApiClient("smoke-test-key")
    ua = client._http.headers["User-Agent"]
    assert ua == f"form4api-py/{args.expected_version}", f"unexpected User-Agent {ua!r}"
    aclient = form4api.AsyncForm4ApiClient("smoke-test-key")
    asyncio.run(aclient.close())
    print(f"  clients construct; User-Agent {ua}")

    # 4. the congress lag field accepts None, both on the type and end to end.
    from form4api._generated import CongressTradeDto

    hints = typing.get_type_hints(CongressTradeDto)
    for field in ("disclosure_lag_days", "date_quality"):
        assert type(None) in typing.get_args(hints[field]), f"CongressTradeDto.{field} does not accept None: {hints[field]}"

    import httpx

    row = {
        "politician": {"bioguideId": None, "slug": "x", "fullName": "X", "party": None, "chamber": "House", "state": "CA"},
        "ticker": "SONY", "assetName": "Sony", "assetType": "Stock", "ownerType": "Self",
        "transactionType": "Purchase", "amountLow": 1001, "amountHigh": 15000,
        "transactionDate": "2026-03-01T00:00:00Z", "disclosureDate": "2026-02-01T00:00:00Z",
        "disclosureLagDays": None, "dateQuality": "transaction_after_disclosure",
    }
    client._http = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=[row])))
    trades = client.congress.trades(ticker="SONY")
    assert isinstance(trades[0], CongressTradeDto)
    assert trades[0].disclosure_lag_days is None and trades[0].date_quality == "transaction_after_disclosure"
    client.close()
    print("  congress lag accepts None (type hint and a mocked response through the client)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as exc:
        print(f"  ASSERTION FAILED: {exc}")
        sys.exit(1)
