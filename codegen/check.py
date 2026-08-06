"""CI gate: fails if form4api/_generated.py is out of sync with the OpenAPI spec.

Mirror of insiderapi-js/codegen/check.mjs. The point of generating is that a new
backend endpoint reaches the SDK by regenerating rather than by someone
remembering to hand-write it in two languages; without this gate that guarantee
is aspirational. Both SDKs drifted to 5 of 12+ endpoint families exactly that way.

GOTCHA (mirrors form4api-mcp): on Windows this can false-drift after a commit,
because git's autocrlf rewrites the working copy to CRLF while freshly generated
output is LF. The tell is a reported drift with an empty diff body. Comparison
below normalises line endings so that cannot fail CI, while every real content
change still does.

Usage:
    py codegen/check.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "form4api" / "_generated.py"
GENERATOR = Path(__file__).resolve().parent / "generate.py"


def main() -> int:
    if not OUTPUT_PATH.exists():
        print("form4api/_generated.py is missing. Run `py codegen/generate.py`.", file=sys.stderr)
        return 1

    before = OUTPUT_PATH.read_bytes()

    result = subprocess.run([sys.executable, str(GENERATOR)])
    if result.returncode != 0:
        return result.returncode

    after = OUTPUT_PATH.read_bytes()

    # Always restore, pass or fail. A check must not mutate the tree it checks —
    # on Windows the regenerated file is LF where the committed one is CRLF, so
    # leaving it behind shows up as a spurious modification in git status.
    OUTPUT_PATH.write_bytes(before)

    def normalise(b: bytes) -> bytes:
        return b.replace(b"\r\n", b"\n")

    if normalise(before) != normalise(after):
        print(
            "\nform4api/_generated.py is out of date with the OpenAPI spec.\n"
            "Run `py codegen/generate.py` and commit the result.\n",
            file=sys.stderr,
        )
        return 1

    print("form4api/_generated.py is in sync with the spec.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
