"""Generate typed resources and response dataclasses from the Form4API OpenAPI spec.

Mirror of insiderapi-js/codegen/generate.mjs, which in turn follows
form4api-mcp/codegen/generate.mjs. Written in Python rather than Node so this
repo keeps a single toolchain.

WHY THIS EXISTS
Both SDKs exposed 5 of 12+ endpoint families. All 6 Pro-gated endpoints and 9 of
the 10 Business-gated ones were unreachable, so a customer paying $149 could not
call Form 144 or 13F holdings from the client library at all. Hand-writing 23
methods twice would have fixed that once and guaranteed the drift returned with
the next endpoint.

WHAT IT DOES NOT DO
It does not regenerate the five hand-written families. Those are a published
PyPI API; regenerating would rename methods and break every user. Hand-written
resources extend the generated bases instead. Move an operation out of
HANDLED_BY_HANDWRITTEN to hand it to codegen.

SYNC *AND* ASYNC
Unlike the JS SDK, this package ships two clients. The existing hand-written
resources are sync-only and are reused by AsyncForm4ApiClient with a
`# type: ignore[arg-type]`, which does not work: the async client's `_get`
returns a coroutine, so `Dataclass(**data)` raises TypeError on every call.
Generated resources therefore come in both flavours so the new surface is
correct. The pre-existing breakage in the hand-written five is tracked
separately.

Usage:
    py codegen/generate.py
    FORM4API_OPENAPI_URL=path/to/openapi.json py codegen/generate.py
"""

from __future__ import annotations

import json
import keyword
import os
import re
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "form4api" / "_generated.py"
SPEC_URL = os.environ.get("FORM4API_OPENAPI_URL", "https://api.form4api.com/openapi/v1.json")

# Operations with no typed response, or that do not belong in an SDK. The
# response-less ones are OpenAPI Stage 1b: they return anonymous objects
# server-side, so there is no schema to bind to. This list shrinks as they gain
# DTOs.
SKIP_OPERATIONS = {
    "HealthLive", "HealthReady", "HealthIngestion",
    "CreateCheckout", "CreateBillingPortal", "CreateApiKey",
    "ExportTransactions", "ExportForm144",
    "InsiderTradingAlias",
    "GetFeaturedTestimonials", "SubmitTestimonial", "JoinUpgradeWaitlist",
    "GetKeyUsage", "GetKeyActivity", "GetUsageHistory",
    "ListWebhooks", "GetWebhookEvents", "CreateWebhook", "DeleteWebhook",
}

# Already exposed by a hand-written resource; generating would produce a second
# method for the same endpoint under a different name.
HANDLED_BY_HANDWRITTEN = {
    "ListTransactions",       # transactions.list()
    "GetInsider",             # insiders.get()
    "GetInsiderTransactions", # insiders.transactions()
    "GetCompany",             # companies.get()
    "GetCompanyInsiders",     # companies.insiders()
    "GetSignals",             # signals.list()
}

# Explicit rather than derived, for the same reason as the JS generator: tags
# are prose and operationIds are not stable vocabulary, so a heuristic is one
# backend rename away from silently reshaping a published API.
TAG_TO_RESOURCE = {
    "Companies": "companies",
    "Congress": "congress",
    "Data Quality": "data_quality",
    "Filings": "filings",
    "Form 144": "form144",
    "Insiders": "insiders",
    "Institutional Holdings (13F-HR)": "holdings",
    "Signals & Sentiment": "signals",
    "Stats": "stats",
    "Status": "status",
    "Transactions": "transactions",
}

METHOD_NAMES = {
    "ListCompanies": "list",
    "ListCongressTrades": "trades",
    "ListCongressPoliticians": "politicians",
    "GetCongressPolitician": "politician",
    "GetCongressTickerRollup": "ticker",
    "GetDataQuality": "get",
    "GetRecentFilings": "recent",
    "GetFiling": "get",
    "ListForm144": "list",
    "ListInsiders": "list",
    "GetInsiderSummary": "summary",
    "GetInsiderScorecard": "scorecard",
    "GetInsiderLeaderboard": "leaderboard",
    "ListHoldings": "list",
    "ListManagers": "managers",
    "ExplainSignal": "explain",
    "GetSentiment": "sentiment",
    "GetConvergenceSignals": "convergence",
    "GetPublicStats": "get",
    "GetStatusHistory": "history",
}


def camel_to_snake(name: str) -> str:
    """Must match _client._camel_to_snake exactly.

    The client runs every response through _normalise, which snake_cases keys
    recursively. If this diverged even slightly, generated dataclass fields
    would not match the dicts they are constructed from and every call would
    raise at runtime rather than at generation time.
    """
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    return re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s).lower()


def safe_ident(name: str) -> str:
    """Python identifier for a wire name, avoiding keywords (`from` -> `from_`)."""
    ident = re.sub(r"[^0-9a-zA-Z_]", "_", camel_to_snake(name))
    if keyword.iskeyword(ident) or ident in {"list", "id"}:
        ident += "_"
    if ident and ident[0].isdigit():
        ident = "_" + ident
    return ident


def py_type(schema: dict | None, required: bool = True) -> str:
    if not schema:
        return "object"
    if "$ref" in schema:
        base = schema["$ref"].split("/")[-1]
    elif schema.get("type") == "array":
        return f"list[{py_type(schema.get('items'))}]"
    else:
        base = {
            "string": "str",
            "integer": "int",
            "number": "float",
            "boolean": "bool",
            "object": "dict[str, object]",
        }.get(schema.get("type"), "object")
    if schema.get("nullable") and required:
        return f"{base} | None"
    return base


def nested_ref(schema: dict | None) -> tuple[str | None, bool]:
    """Resolve a property schema to (generated class name, is_list).

    Returns (None, False) for scalars, free-form objects, and arrays of
    scalars — anything with no generated dataclass to hydrate into.
    """
    if not schema:
        return None, False
    if "$ref" in schema:
        return schema["$ref"].split("/")[-1], False
    if schema.get("type") == "array":
        items = schema.get("items") or {}
        if "$ref" in items:
            return items["$ref"].split("/")[-1], True
    return None, False


def render_dataclass(name: str, schema: dict) -> str:
    props: dict = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    if not props:
        return f"@dataclass\nclass {name}:\n    \"\"\"Opaque payload — the spec declares no properties.\"\"\"\n\n"

    # EVERY field is optional and defaults to None, including ones the spec
    # marks required.
    #
    # This is deliberate and asymmetric with the annotations you might expect.
    # The JS SDK erases types at runtime, so it tolerates any payload the
    # backend sends. If Python enforced `required` strictly, the same API
    # response would work in one SDK and raise TypeError deep inside parsing in
    # the other — and the caller could not work around it. A missing field
    # surfacing as None at the use site is strictly more recoverable than an
    # exception at parse time, and it means an older SDK keeps working when the
    # backend changes a field's optionality.
    #
    # The annotations stay honest about this: everything is `T | None`, so type
    # checkers make callers handle absence rather than trusting the wire.
    lines = [f"@dataclass\nclass {name}:"]
    if schema.get("description"):
        lines.append(f'    """{schema["description"]}"""\n')
    for prop, ps in sorted(props.items()):
        field = safe_ident(prop)
        annotation = py_type(ps, False)
        if not annotation.endswith("| None"):
            annotation = f"{annotation} | None"
        lines.append(f"    {field}: {annotation} = None")
    lines.append("")
    lines.append("    @classmethod")
    lines.append(f'    def _from_dict(cls, data: dict) -> "{name}":')
    lines.append('        """Build from an API payload, ignoring unknown keys.')
    lines.append("")
    lines.append("        Constructing with **data directly (as the hand-written resources do)")
    lines.append("        means the SDK raises TypeError the moment the backend adds a field.")
    lines.append('        Filtering keeps older SDK versions working against a newer API."""')
    lines.append("        known = {f.name for f in fields(cls)}")

    # Nested objects have to be hydrated explicitly, or the annotation lies.
    #
    # cls(**data) assigns whatever the payload holds, so a field annotated
    # `list[LeaderboardEntry]` was being handed a list of plain dicts. The
    # client's _normalise already snake_cases keys recursively, which made the
    # breakage subtle: `result.insiders[0]["insider_cik"]` worked while the
    # documented `result.insiders[0].insider_cik` raised AttributeError. 31
    # fields across this SDK were affected.
    #
    # Names resolve at call time, so a nested class defined later in the module
    # is fine and no ordering constraint is introduced.
    nested: list[tuple[str, str, bool]] = []
    for prop, ps in sorted(props.items()):
        target, is_list = nested_ref(ps)
        if target:
            nested.append((safe_ident(prop), target, is_list))

    if not nested:
        lines.append("        return cls(**{k: v for k, v in data.items() if k in known})")
    else:
        lines.append("        kwargs = {k: v for k, v in data.items() if k in known}")
        for field, target, is_list in nested:
            if is_list:
                lines.append(f'        if isinstance(kwargs.get("{field}"), list):')
                lines.append(
                    f'            kwargs["{field}"] = [{target}._from_dict(i) '
                    f'if isinstance(i, dict) else i for i in kwargs["{field}"]]'
                )
            else:
                lines.append(f'        if isinstance(kwargs.get("{field}"), dict):')
                lines.append(
                    f'            kwargs["{field}"] = {target}._from_dict(kwargs["{field}"])'
                )
        lines.append("        return cls(**kwargs)")
    lines.append("")
    return "\n".join(lines) + "\n"


def path_params(template: str) -> list[str]:
    return re.findall(r"\{([^}]+)\}", template)


def render_method(op: dict, template: str, is_async: bool) -> str:
    method_name = METHOD_NAMES[op["operationId"]]
    schema = (
        op.get("responses", {}).get("200", {})
        .get("content", {}).get("application/json", {}).get("schema")
    )
    ret = py_type(schema)

    pp = path_params(template)
    query = [p for p in (op.get("parameters") or []) if p.get("in") == "query"]

    args = ["self"] + [f"{safe_ident(p)}: str" for p in pp]
    if query:
        args.append("*")
        for p in query:
            args.append(f"{safe_ident(p['name'])}: {py_type(p.get('schema'), False)} | None = None")

    url = re.sub(r"\{([^}]+)\}", lambda m: f"{{{safe_ident(m.group(1))}}}", template)

    body: list[str] = []
    if query:
        body.append("        params = {")
        for p in query:
            body.append(f'            "{p["name"]}": {safe_ident(p["name"])},')
        body.append("        }")
        body.append('        params = {k: str(v) for k, v in params.items() if v is not None}')
        call_args = f'f"{url}", params=params'
    else:
        call_args = f'f"{url}"'

    await_kw = "await " if is_async else ""
    body.append(f"        data = {await_kw}self._client._get({call_args})")

    # Unwrap the element type for list returns so items are dataclasses too.
    inner = ret[5:-1] if ret.startswith("list[") else ret
    if inner in ("str", "int", "float", "bool", "object") or inner.startswith("dict["):
        body.append("        return data")
    elif ret.startswith("list["):
        body.append(f"        return [{inner}._from_dict(item) for item in data]")
    else:
        body.append(f"        return {inner}._from_dict(data)")

    doc = op.get("summary") or ""
    desc = op.get("description") or ""
    docstring = ""
    if doc or desc:
        text = doc if doc == desc or not desc else f"{doc}\n\n        {desc}" if doc else desc
        docstring = f'        """{text}"""\n'

    prefix = "async def" if is_async else "def"
    return f"    {prefix} {method_name}({', '.join(args)}) -> {ret}:\n{docstring}" + "\n".join(body) + "\n"


def main() -> int:
    print(f"Fetching OpenAPI spec from {SPEC_URL}")
    if SPEC_URL.startswith("http"):
        with urllib.request.urlopen(SPEC_URL, timeout=60) as fh:
            spec = json.load(fh)
    else:
        spec = json.loads(Path(SPEC_URL).read_text(encoding="utf-8"))

    schemas = (spec.get("components") or {}).get("schemas") or {}
    dataclasses_out = [render_dataclass(name, s) for name, s in sorted(schemas.items())]

    by_resource: dict[str, list[tuple[dict, str]]] = {}
    skipped: list[str] = []

    for template, item in spec["paths"].items():
        for method, op in item.items():
            if method != "get":
                continue
            oid = op.get("operationId")
            if not oid:
                continue
            if oid in SKIP_OPERATIONS:
                skipped.append(f"{oid} (skipped)")
                continue
            if oid in HANDLED_BY_HANDWRITTEN:
                skipped.append(f"{oid} (hand-written)")
                continue
            tag = (op.get("tags") or [None])[0]
            resource = TAG_TO_RESOURCE.get(tag)
            if not resource:
                skipped.append(f'{oid} (no resource for tag "{tag}")')
                continue
            by_resource.setdefault(resource, []).append((op, template))

    classes: list[str] = []
    generated = 0
    for resource, ops in sorted(by_resource.items()):
        cls = "Generated" + "".join(p.title() for p in resource.split("_")) + "Resource"
        for is_async, suffix in ((False, ""), (True, "Async")):
            name = cls.replace("Generated", f"Generated{suffix}") if suffix else cls
            methods = sorted(ops, key=lambda o: METHOD_NAMES[o[0]["operationId"]])
            body = "\n".join(render_method(op, tpl, is_async) for op, tpl in methods)
            classes.append(
                f"class {name}:\n"
                f"    def __init__(self, client) -> None:\n"
                f"        self._client = client\n\n{body}"
            )
        generated += len(ops)

    header = '''"""AUTOGENERATED by codegen/generate.py — do not edit by hand.

Regenerate with `py codegen/generate.py`; `py codegen/check.py` gates CI.

Source of truth is the Form4API OpenAPI document, so a new backend endpoint
reaches the SDK by regenerating rather than by hand-writing it in two languages.

Field names are snake_case because the client runs every response through
_normalise() before it reaches these classes.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

'''

    OUTPUT_PATH.write_text(
        header + "\n".join(dataclasses_out) + "\n" + "\n\n".join(classes) + "\n",
        encoding="utf-8-sig",  # BOM, matching the rest of the package
        newline="",
    )

    print(f"Wrote {OUTPUT_PATH}")
    print(f"  {len(schemas)} dataclasses, {generated} operations across {len(by_resource)} resources (sync + async)")
    for s in skipped:
        print(f"  skipped: {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
