"""Pre-publish gate for the form4api Python SDK.

    py scripts/release_check.py [--offline] [--keep]        (Windows)
    python scripts/release_check.py [--offline] [--keep]    (CI)

Stages, stopping at the first failure:

  1. Version sync      pyproject == __version__ == top CHANGELOG entry
  2. Build             sdist + wheel into a fresh temp directory
  3. Static checks     twine check --strict, check-wheel-contents, and the wheel
                       must contain every module under form4api/ and nothing else
  4. Install           fresh venv, pip install the WHEEL (not the repo, not -e)
  5. Smoke test        import everything from the installed wheel, cwd outside the repo
  6. Live contract     real API responses vs the live OpenAPI spec, using the
                       INSTALLED package. Needs FORM4API_TEST_KEY.
  7. Not published     this version must not already be on PyPI (FAIL; only a
                       WARN under --offline, so CI can still run on a released version)

--offline  skip stage 6 (CI uses this; there is no key there). Also downgrades stage 7 to a warning.
--keep     keep the temp directories (they are removed by default).

The dev tools come from the dev extra:  pip install -e ".[dev]"

This script never uploads anything and never prints the API key.
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
PACKAGE = "form4api"
KEY_ENV = "FORM4API_TEST_KEY"
# Directories that must never leak into the build copy: stale artefacts are the
# whole reason the build happens in a temp tree.
COPY_IGNORE = shutil.ignore_patterns(
    ".git", ".venv", "venv", "dist", "build", "*.egg-info", "__pycache__", ".pytest_cache", ".github", "node_modules"
)


class StageFailed(Exception):
    pass


class StageWarn(Exception):
    """The stage found a problem that only blocks a real release (not --offline)."""


class Ctx:
    def __init__(self, keep: bool) -> None:
        self.keep = keep
        self.tmp = Path(tempfile.mkdtemp(prefix="form4api-release-check-")).resolve()
        self.version = ""
        self.sdist: Path | None = None
        self.wheel: Path | None = None
        self.venv_py: Path | None = None

    def cleanup(self) -> None:
        if self.keep:
            print(f"\nTemp directory kept: {self.tmp}")
            return

        def _force(func, path, _exc):  # Windows: read-only files inside venvs
            os.chmod(path, 0o700)
            func(path)

        shutil.rmtree(self.tmp, onerror=_force)


def run(cmd: list[str], *, cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        [str(c) for c in cmd], cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return proc


def redact(text: str) -> str:
    key = os.environ.get(KEY_ENV)
    return text.replace(key, "***") if key else text


def tail(text: str, n: int = 40) -> str:
    lines = redact(text).strip().splitlines()
    return "\n".join(lines[-n:])


def need(proc: subprocess.CompletedProcess, what: str) -> str:
    """Raise StageFailed with the real output unless the process succeeded."""
    if proc.returncode != 0:
        raise StageFailed(f"{what} exited {proc.returncode}\n{tail(proc.stdout)}\n{tail(proc.stderr)}".rstrip())
    return proc.stdout


def pyproject_version() -> str:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


# ---------------------------------------------------------------------------
# Stage 1
# ---------------------------------------------------------------------------

def stage_version(ctx: Ctx) -> list[str]:
    out: list[str] = []
    version = pyproject_version()
    ctx.version = version
    out.append(f"pyproject version: {version}")

    # __version__: find where it is defined.
    tree = ast.parse((ROOT / PACKAGE / "__init__.py").read_text(encoding="utf-8-sig"))
    source_version = None
    defined = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__version__" for t in node.targets):
            defined = True
            if isinstance(node.value, ast.Constant):
                source_version = node.value.value
        if isinstance(node, ast.ImportFrom) and any((a.asname or a.name) == "__version__" for a in node.names):
            defined = True
    if not defined:
        raise StageFailed("form4api/__init__.py does not define __version__")
    if source_version is not None:
        if source_version != version:
            raise StageFailed(f"form4api.__version__ is {source_version!r} but pyproject says {version!r}")
        out.append(f"__version__ literal: {source_version}")
    else:
        out.append("__version__ is derived from installed package metadata (pyproject is the single source); stage 5 checks it on the installed wheel")

    # Top CHANGELOG entry: "## 0.9.0 — 2026-10-05"; "## Unreleased" is skipped.
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8-sig")
    m = re.search(r"^##\s+\[?v?(\d+\.\d+\.\d+[0-9A-Za-z.+-]*)\]?", changelog, re.MULTILINE)
    if not m:
        raise StageFailed("CHANGELOG.md has no version heading like '## 0.9.0 — date'")
    if m.group(1) != version:
        raise StageFailed(f"top CHANGELOG.md entry is {m.group(1)!r} but pyproject says {version!r}")
    out.append(f"CHANGELOG top entry: {m.group(1)}")

    return out


# ---------------------------------------------------------------------------
# Stage 2
# ---------------------------------------------------------------------------

def stage_build(ctx: Ctx) -> list[str]:
    if run([sys.executable, "-c", "import build"]).returncode != 0:
        raise StageFailed("the `build` package is missing. Install the dev extra: pip install -e \".[dev]\"")
    # Build from a copy of the tree minus dist/, build/ and egg-info, so a stale
    # artefact (or stale build/lib) can never be what gets tested.
    src = ctx.tmp / "src"
    shutil.copytree(ROOT, src, ignore=COPY_IGNORE)
    dist = ctx.tmp / "dist"
    need(run([sys.executable, "-m", "build", "--sdist", "--wheel", "--outdir", dist, src]), "python -m build")
    wheels = sorted(dist.glob("*.whl"))
    sdists = sorted(dist.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise StageFailed(f"expected exactly one wheel and one sdist in {dist}, found {[p.name for p in dist.iterdir()]}")
    ctx.wheel, ctx.sdist = wheels[0], sdists[0]
    for art in (ctx.wheel, ctx.sdist):
        if f"-{ctx.version}" not in art.name:
            raise StageFailed(f"{art.name} does not carry version {ctx.version}")
    return [f"built {ctx.sdist.name}", f"built {ctx.wheel.name}", f"output dir: {dist}"]


# ---------------------------------------------------------------------------
# Stage 3
# ---------------------------------------------------------------------------

def stage_static(ctx: Ctx) -> list[str]:
    assert ctx.wheel and ctx.sdist
    out: list[str] = []
    for mod, hint in (("twine", "twine"), ("check_wheel_contents", "check-wheel-contents")):
        if run([sys.executable, "-c", f"import {mod}"]).returncode != 0:
            raise StageFailed(f"`{hint}` is missing. Install the dev extra: pip install -e \".[dev]\"")

    need(run([sys.executable, "-m", "twine", "check", "--strict", ctx.sdist, ctx.wheel]), "twine check --strict")
    out.append("twine check --strict: both files OK")

    proc = run([sys.executable, "-m", "check_wheel_contents", ctx.wheel])
    need(proc, "check-wheel-contents")
    out.append("check-wheel-contents: OK")

    # Source modules <-> wheel contents.
    expected = {
        p.relative_to(ROOT).as_posix()
        for p in (ROOT / PACKAGE).rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix not in {".pyc", ".pyo"}
    }
    with zipfile.ZipFile(ctx.wheel) as zf:
        names = {n for n in zf.namelist() if not n.endswith("/")}
    in_pkg = {n for n in names if n.startswith(PACKAGE + "/")}
    missing = sorted(expected - in_pkg)
    if missing:
        raise StageFailed("wheel is missing files present under form4api/ in the source tree:\n  " + "\n  ".join(missing))
    extra = sorted(in_pkg - expected)
    if extra:
        raise StageFailed("wheel contains files under form4api/ that are not in the source tree:\n  " + "\n  ".join(extra))

    allowed_top = {PACKAGE, f"{PACKAGE}-{ctx.version}.dist-info"}
    top = {n.split("/")[0] for n in names}
    unexpected = sorted(top - allowed_top)
    if unexpected:
        raise StageFailed(f"unexpected top-level entries in the wheel: {unexpected} (tests/codegen/etc. must not ship)")
    needed_meta = {f"{PACKAGE}-{ctx.version}.dist-info/{f}" for f in ("METADATA", "WHEEL", "RECORD")}
    if needed_meta - names:
        raise StageFailed(f"wheel is missing dist-info files: {sorted(needed_meta - names)}")
    out.append(f"wheel has all {len(expected)} files from form4api/ and only {sorted(top)}")
    return out


# ---------------------------------------------------------------------------
# Stage 4
# ---------------------------------------------------------------------------

def stage_install(ctx: Ctx) -> list[str]:
    assert ctx.wheel
    venv_dir = ctx.tmp / "venv"
    need(run([sys.executable, "-m", "venv", venv_dir]), "python -m venv")
    ctx.venv_py = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    need(
        run([ctx.venv_py, "-m", "pip", "install", "--disable-pip-version-check", "--no-input", ctx.wheel]),
        "pip install <wheel>",
    )
    listing = need(run([ctx.venv_py, "-m", "pip", "list", "--format=freeze", "--disable-pip-version-check"]), "pip list")
    pkgs = ", ".join(sorted(line.strip() for line in listing.splitlines() if not line.startswith(("pip==", "setuptools=="))))
    return [f"installed {ctx.wheel.name} into {venv_dir}", f"venv packages: {pkgs}"]


# ---------------------------------------------------------------------------
# Stage 5
# ---------------------------------------------------------------------------

def _isolated_cwd(ctx: Ctx) -> Path:
    cwd = ctx.tmp / "elsewhere"
    cwd.mkdir(exist_ok=True)
    return cwd


def stage_smoke(ctx: Ctx) -> list[str]:
    assert ctx.venv_py
    proc = run(
        [ctx.venv_py, "-I", SCRIPTS / "smoke_installed.py", "--expected-version", ctx.version, "--forbid-root", ROOT],
        cwd=_isolated_cwd(ctx),
    )
    if proc.returncode != 0:
        raise StageFailed(f"smoke test exited {proc.returncode}\n{tail(proc.stdout)}\n{tail(proc.stderr)}".rstrip())
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Stage 6
# ---------------------------------------------------------------------------

def stage_contract(ctx: Ctx) -> list[str]:
    assert ctx.venv_py and ctx.wheel
    if not os.environ.get(KEY_ENV):
        raise StageFailed(
            f"{KEY_ENV} is not set. The live contract stage needs an API key (a Business-plan key, "
            "because /v1/signals is plan-gated). Set it and re-run, or pass --offline to skip this stage."
        )
    print(f"      {KEY_ENV} is set (value not shown)")
    # The wheel plus its `contract` extra (the OpenAPI validator), in the same temp venv.
    need(
        run([ctx.venv_py, "-m", "pip", "install", "--disable-pip-version-check", "--no-input", f"{ctx.wheel}[contract]"]),
        "pip install <wheel>[contract]",
    )
    proc = run(
        [ctx.venv_py, "-I", SCRIPTS / "contract_check.py", "--forbid-root", ROOT],
        cwd=_isolated_cwd(ctx),
        env=os.environ.copy(),
    )
    lines = [line.rstrip() for line in redact(proc.stdout).splitlines() if line.strip()]
    if proc.returncode != 0:
        raise StageFailed("live contract check failed\n" + "\n".join(lines) + ("\n" + tail(proc.stderr) if proc.stderr.strip() else ""))
    return [line.strip() for line in lines]


# ---------------------------------------------------------------------------
# Stage 7
# ---------------------------------------------------------------------------

def stage_not_published(ctx: Ctx, offline: bool = False) -> list[str]:
    """PyPI refuses to re-upload a version, so catch it before twine does."""
    url = f"https://pypi.org/pypi/{PACKAGE}/{ctx.version}/json"
    req = urllib.request.Request(url, headers={"User-Agent": "form4api-py-release-check"})
    try:
        with urllib.request.urlopen(req, timeout=20):
            published = True
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise StageFailed(f"PyPI answered HTTP {exc.code} for {url}; cannot confirm {ctx.version} is unpublished") from None
        published = False
    except OSError as exc:
        if offline:
            raise StageWarn(f"could not reach PyPI ({exc}); did not verify that {ctx.version} is unpublished") from None
        raise StageFailed(f"could not reach PyPI to verify {ctx.version} is unpublished: {exc}") from None
    if published:
        msg = f"{PACKAGE} {ctx.version} is already published on PyPI; PyPI will reject a re-upload. Bump the version."
        if offline:
            raise StageWarn(msg)
        raise StageFailed(msg)
    return [f"{PACKAGE} {ctx.version} is not on PyPI yet"]


# ---------------------------------------------------------------------------

STAGES = [
    ("Version sync", stage_version),
    ("Build", stage_build),
    ("Static checks", stage_static),
    ("Install in isolation", stage_install),
    ("Smoke test installed package", stage_smoke),
    ("Live contract", stage_contract),
    ("Version not yet published", stage_not_published),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="Pre-publish gate for the form4api Python SDK.")
    ap.add_argument("--offline", action="store_true", help="skip the live contract stage (no API key needed)")
    ap.add_argument("--keep", action="store_true", help="keep the temp directories")
    args = ap.parse_args()

    ctx = Ctx(keep=args.keep)
    results: list[tuple[str, str]] = []
    failed = False
    try:
        for i, (name, fn) in enumerate(STAGES, start=1):
            label = f"[{i}/{len(STAGES)}] {name}"
            if failed:
                results.append((label, "NOT RUN"))
                continue
            if name == "Live contract" and args.offline:
                print(f"{label}: SKIP (--offline)")
                results.append((label, "SKIP"))
                continue
            print(f"{label} ...")
            try:
                details = fn(ctx, args.offline) if fn is stage_not_published else fn(ctx)
            except StageWarn as exc:
                print(f"{label}: WARN (--offline)")
                print(f"      {exc}")
                results.append((label, "WARN"))
                continue
            except StageFailed as exc:
                print(f"{label}: FAIL")
                for line in str(exc).splitlines():
                    print(f"      {line}")
                results.append((label, "FAIL"))
                failed = True
                continue
            except Exception as exc:  # noqa: BLE001 - a crashing stage is a failing stage
                print(f"{label}: FAIL (unexpected {type(exc).__name__}: {redact(str(exc))})")
                results.append((label, "FAIL"))
                failed = True
                continue
            for line in details:
                print(f"      {line}")
            print(f"{label}: PASS")
            results.append((label, "PASS"))
    finally:
        print("\nSummary")
        for label, status in results:
            print(f"  {status:<8} {label}")
        verdict = "FAILED" if failed else ("PASSED (live contract stage skipped)" if args.offline else "PASSED")
        print(f"\nrelease_check {verdict}")
        ctx.cleanup()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
