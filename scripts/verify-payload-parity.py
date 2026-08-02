#!/usr/bin/env python3
"""Prove that patches/ changes nothing its source lane did not already change.

This is the safety interlock behind rebase/<tag>.rules. Re-anchoring a hunk to a
newer kernel means editing CONTEXT, and the whole question a reviewer has is
"did that edit quietly change what the patch does?".

The check: for every patch, extract the ordered list of added ('+') and removed
('-') lines from its source (upstream/ or ceralive/) and from patches/, and
require them to be identical. Context lines and @@ headers are deliberately
ignored -- those are exactly what a re-anchor is allowed to move.

If this passes, patches/ is a repackaging of its source, not a fork of its
behaviour: for the upstream lane that means "still Ross Cawston's work", and for
the first-party lane it means "still exactly what ceralive/ says", so patches/
cannot be hand-edited into carrying a change no reviewable source file shows. If
it fails, a rule overstepped and the conflict belongs in docs/REBASE-<tag>.md as
a stop, not in a rule.

Usage:  scripts/verify-payload-parity.py
Exit:   0 identical, 1 divergent, 2 structural problem
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATCHES_DIR = ROOT / "patches"
# Deliberately NOT imported from build-series.py: this checker is the second,
# independent opinion, so it re-derives a patch's lane from the filesystem.
SOURCE_DIRS = (ROOT / "upstream", ROOT / "ceralive")

# File-header lines share the '+'/'-' prefix with real payload but are metadata.
FILE_HEADER_RE = re.compile(r"^(\+\+\+|---) ")
# Payload-free macOS noise the converter drops on purpose.
DS_STORE_RE = re.compile(r"^Binary files .*\.DS_Store .* differ$")


def diff_body(lines: list[str]) -> list[str]:
    """Drop the mail header, if any. A bare '---' ends it, per mailbox convention."""
    for i, line in enumerate(lines):
        if line == "---":
            return lines[i + 1 :]
    return lines


def payload(path: Path) -> list[str]:
    """Ordered added/removed lines, excluding diff file headers."""
    lines = path.read_text(encoding="utf-8", errors="surrogateescape").splitlines()
    # NB: `line[:1] in "+-"` would be true for the empty string, since "" is a
    # substring of everything. Compare against a tuple.
    return [
        line
        for line in diff_body(lines)
        if line[:1] in ("+", "-") and not FILE_HEADER_RE.match(line)
    ]


def dropped_ds_store(path: Path) -> int:
    lines = path.read_text(encoding="utf-8", errors="surrogateescape").splitlines()
    return sum(1 for line in lines if DS_STORE_RE.match(line))


def find_source(name: str) -> Path | None:
    """The one lane directory holding `name`. Two hits is ambiguous provenance."""
    hits = [d / name for d in SOURCE_DIRS if (d / name).is_file()]
    return hits[0] if len(hits) == 1 else None


def main() -> int:
    patch_files = sorted(PATCHES_DIR.glob("*.patch"))
    if not patch_files:
        print("no patches found; run scripts/build-series.py first", file=sys.stderr)
        return 2

    failures = 0
    for converted in patch_files:
        original = find_source(converted.name)
        if original is None:
            lanes = ", ".join(d.name + "/" for d in SOURCE_DIRS)
            print(
                f"FAIL {converted.name}: needs exactly one source in {lanes}",
                file=sys.stderr,
            )
            failures += 1
            continue

        lane = original.parent.name
        want = payload(original)
        got = payload(converted)

        if want == got:
            noise = dropped_ds_store(original)
            note = f", dropped {noise} .DS_Store stanza(s)" if noise else ""
            print(
                f"OK   {converted.name}: {len(got)} payload lines "
                f"identical to {lane}/{note}"
            )
            continue

        failures += 1
        print(f"FAIL {converted.name}: payload diverges from {lane}/", file=sys.stderr)
        print(f"     {lane} {len(want)} lines, converted {len(got)}", file=sys.stderr)
        for i, (a, b) in enumerate(zip(want, got)):
            if a != b:
                print(f"     first divergence at payload line {i}:", file=sys.stderr)
                print(f"       {lane:<9}: {a!r}", file=sys.stderr)
                print(f"       converted: {b!r}", file=sys.stderr)
                break

    if failures:
        print(
            f"\n{failures} patch(es) diverge. A rebase rule changed behaviour; "
            "that belongs in the stop ledger, not in rebase/*.rules.",
            file=sys.stderr,
        )
        return 1

    print(f"\nall {len(patch_files)} patches: payload byte-identical to their source.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
