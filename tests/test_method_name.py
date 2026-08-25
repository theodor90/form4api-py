"""The generator derives a method name when no override is pinned.

It used to raise instead, which is why this SDK could not regenerate at all
between 2026-08-04 (/v1/filings) and 2026-08-25 (/v1/insiders/directory): a new
backend endpoint took codegen down until someone hand-added a line, and with CI
billing-blocked nobody saw it go red.

So the rule is load-bearing and pinned here. Deriving a name wrong is worse
than not deriving one — the method ships, someone imports it, and correcting it
afterwards is a breaking rename.

Mirrors tests/methodNames.test.ts in the JS SDK. The two derivations must agree
on which words are dropped; they differ only in casing.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "codegen"))

from method_name import derive_method_name  # noqa: E402


def test_drops_the_resource_the_method_already_lives_on() -> None:
    # filings.get_recent_filings() says "filings" twice.
    assert derive_method_name("GetRecentFilings", "filings") == "recent"
    assert derive_method_name("GetInsiderScorecard", "insiders") == "scorecard"
    assert derive_method_name("GetConvergenceSignals", "signals") == "convergence"
    assert derive_method_name("GetStatusHistory", "status") == "history"


def test_falls_back_to_the_verb_when_the_resource_was_the_whole_name() -> None:
    # What makes companies.list() and filings.get() read correctly.
    assert derive_method_name("ListCompanies", "companies") == "list"
    assert derive_method_name("ListInsiders", "insiders") == "list"
    assert derive_method_name("GetFiling", "filings") == "get"
    assert derive_method_name("GetDataQuality", "data_quality") == "get"


def test_derives_the_two_endpoints_that_had_been_breaking_codegen() -> None:
    assert derive_method_name("ListFilings", "filings") == "list"
    assert derive_method_name("GetInsiderDirectory", "insiders") == "directory"


def test_matches_exact_or_simple_plural_never_a_prefix() -> None:
    # A looser test would strip "Sentiment" for a resource called "signals"
    # and collapse two different endpoints onto signals.get().
    assert derive_method_name("GetSentiment", "signals") == "sentiment"
    assert derive_method_name("ListManagers", "holdings") == "managers"


def test_handles_a_resource_carrying_digits() -> None:
    # "Form144" must stay one word. Split into "Form" + "144", neither half
    # matches the resource and this derives to form144() instead of list().
    assert derive_method_name("ListForm144", "form144") == "list"


def test_snake_cases_a_multi_word_remainder() -> None:
    # The one place the two SDKs differ: JS camelCases this to tickerRollup.
    assert derive_method_name("GetCongressTickerRollup", "congress") == "ticker_rollup"


def test_already_published_names_stay_pinned() -> None:
    """Every shipped name is kept as an explicit override even where the
    derived value agrees, so no upstream operationId rename can quietly change
    a method someone has already imported."""
    source = (Path(__file__).resolve().parents[1] / "codegen" / "generate.py").read_text(
        encoding="utf-8"
    )
    block = source[source.index("METHOD_NAME_OVERRIDES = {") :]
    block = block[: block.index("\n}")]

    # These two would derive to something else entirely — the case the
    # override list exists for.
    assert '"GetCongressTickerRollup": "ticker"' in block
    assert '"GetPublicStats": "get"' in block

    for operation_id in (
        "ListCompanies",
        "ListCongressTrades",
        "GetInsiderLeaderboard",
        "ListHoldings",
        "ExplainSignal",
        "GetSentiment",
    ):
        assert f'"{operation_id}":' in block, f"{operation_id} must stay pinned"
