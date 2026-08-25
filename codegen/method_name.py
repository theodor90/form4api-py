"""Deriving a generated method's name from its operationId.

Its own module rather than a helper inside generate.py so it can be imported
and tested without running the generator. The rule is load-bearing: a name
derived wrong still ships, someone imports it, and correcting it afterwards is
a breaking rename.

Mirrors codegen/methodName.mjs in the JS SDK. The two must agree on which words
get dropped — they differ only in casing, since Python joins with underscores
and JS camelCases.
"""

from __future__ import annotations

import re

# Leading verbs stripped before a name is derived. Longest first: "Explain"
# must be tried before any prefix of it would be.
VERB_PREFIXES = ("Explain", "Create", "Delete", "Export", "Submit", "List", "Get")

# PascalCase word split. Trailing digits stay attached to the word they belong
# to, so "Form144" is one word rather than "Form" + "144" — split apart, neither
# half matches a resource called `form144` and ListForm144 derives to
# `form144()` instead of `list()`.
_WORD = re.compile(r"[A-Z][a-z]*[0-9]*|[0-9]+")

# Resource names are snake_case here (`data_quality`), so split on the
# underscore as well as on case.
_RESOURCE_WORD = re.compile(r"[A-Za-z][a-z0-9]*")


def words_of(s: str) -> list[str]:
    """PascalCase split: GetInsiderDirectory -> Get, Insider, Directory."""
    return _WORD.findall(s)


def derive_method_name(operation_id: str, resource: str) -> str:
    """Method name for an operation with no override.

    Strips the leading verb, then drops any word naming the resource the method
    already lives on — ``filings.get_recent_filings()`` says "filings" twice.
    What is left is the method: ListFilings on ``filings`` -> ``list()``,
    GetInsiderDirectory on ``insiders`` -> ``directory()``. When nothing is
    left, the verb IS the name, which is how ``companies.list()`` and
    ``filings.get()`` read.

    Matching is exact-or-simple-plural on purpose. A looser prefix test would
    strip "Sentiment" for a resource called "signals" the moment someone made
    it fuzzy, and silently collapse two endpoints onto ``signals.get()``.
    """
    verb = next((v for v in VERB_PREFIXES if operation_id.startswith(v)), "")
    resource_words = [w.lower() for w in _RESOURCE_WORD.findall(resource)]

    def is_resource_word(w: str) -> bool:
        lw = w.lower()
        return any(r == lw or r == f"{lw}s" or lw == f"{r}s" for r in resource_words)

    kept = [w for w in words_of(operation_id[len(verb):]) if not is_resource_word(w)]
    if not kept:
        return (verb or "Get").lower()
    return "_".join(w.lower() for w in kept)
