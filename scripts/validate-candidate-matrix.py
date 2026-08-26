#!/usr/bin/env python3
"""Prove the candidate reconciliation matrix is complete, not merely present.

A screening round is only auditable if every candidate carries every finding --
including the boring ones. "No overlap" and "no follow-up landed" are results; an
absent field is not. So this checker refuses a matrix with a missing alias, a
missing field, an empty field, a duplicate, a disposition outside the closed set,
or a discovery-snapshot digest that is not the frozen one the round was screened
against.

Usage:
    scripts/validate-candidate-matrix.py docs/UPSTREAM-STATUS.md \\
        --aliases M1,M2,...,U7 --source-sha256 <64-hex>

Exit: 0 complete, 1 incomplete, 2 misuse.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

BEGIN = "<!-- candidate-matrix: begin -->"
END = "<!-- candidate-matrix: end -->"

ALIAS_RE = re.compile(r"^####\s+(?P<alias>[A-Z][0-9]+)\b")
FIELD_RE = re.compile(r"^-\s+(?P<key>[A-Za-z][A-Za-z0-9 /()-]*):\s*(?P<value>.+?)\s*$")
SNAPSHOT_RE = re.compile(r"^Discovery snapshot sha256:\s*(?P<digest>[0-9a-f]{64})\s*$")
DEFERRED_NOTES_RE = re.compile(
    r"^failed route:\s*(?P<route>\S(?:.*\S)?);\s*"
    r"attempt date:\s*(?P<attempt_date>\d{4}-\d{2}-\d{2})$",
    re.IGNORECASE,
)

REQUIRED_FIELDS = (
    "Capture revision",
    "Subject",
    "Identity",
    "Thread review",
    "Prerequisite graph",
    "Follow-up sweep",
    "Apply base-only",
    "Apply stacked",
    "Overlap",
    "Build result",
    "Regression state",
    "Retire trigger",
    "Disposition",
)

DISPOSITIONS = (
    "IN",
    "OUT",
    "ALREADY-IN-BASE / NO IMPORT",
    "ALREADY CARRIED",
    "RETIRED",
    "DEFERRED",
)

PARSED_FIELDS = frozenset((*REQUIRED_FIELDS, "Notes"))


def extract_block(text: str) -> list[str]:
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise SystemExit(
            f"error: expected exactly one {BEGIN} / {END} pair in the document"
        )
    body = text.split(BEGIN, 1)[1].split(END, 1)[0]
    return body.splitlines()


def parse(lines: list[str]) -> tuple[str | None, dict[str, dict[str, str]], list[str]]:
    problems: list[str] = []
    snapshot: str | None = None
    entries: dict[str, dict[str, str]] = {}
    current: str | None = None
    for lineno, raw in enumerate(lines, 1):
        line = raw.strip()
        snap = SNAPSHOT_RE.match(line)
        if snap:
            if snapshot is not None:
                problems.append(f"line {lineno}: a second discovery snapshot digest")
            snapshot = snap.group("digest")
            continue
        alias = ALIAS_RE.match(line)
        if alias:
            current = alias.group("alias")
            if current in entries:
                problems.append(f"line {lineno}: alias {current} appears twice")
            entries.setdefault(current, {})
            continue
        field = FIELD_RE.match(line)
        if not field or current is None:
            continue
        key, value = field.group("key").strip(), field.group("value").strip()
        if key not in PARSED_FIELDS:
            continue
        if key in entries[current]:
            problems.append(f"line {lineno}: {current} repeats field {key!r}")
        entries[current][key] = value
    return snapshot, entries, problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", type=Path)
    parser.add_argument("--aliases", required=True)
    parser.add_argument("--source-sha256", required=True)
    args = parser.parse_args()

    wanted = [alias.strip() for alias in args.aliases.split(",") if alias.strip()]
    if len(set(wanted)) != len(wanted):
        print("error: --aliases repeats an alias", file=sys.stderr)
        return 2

    snapshot, entries, problems = parse(
        extract_block(args.document.read_text(encoding="utf-8"))
    )

    if snapshot is None:
        problems.append(
            "the matrix records no discovery snapshot digest; the round has to name "
            "the exact bytes it was screened against"
        )
    elif snapshot != args.source_sha256:
        problems.append(
            f"discovery snapshot digest {snapshot} is not the frozen "
            f"{args.source_sha256}"
        )

    for alias in wanted:
        if alias not in entries:
            problems.append(f"{alias}: no row")
            continue
        for key in REQUIRED_FIELDS:
            value = entries[alias].get(key)
            if not value:
                problems.append(f"{alias}: field {key!r} is missing or empty")
        disposition = entries[alias].get("Disposition", "")
        if disposition and disposition not in DISPOSITIONS:
            problems.append(
                f"{alias}: disposition {disposition!r} is not one of {DISPOSITIONS}"
            )
        if disposition == "DEFERRED":
            notes = entries[alias].get("Notes", "")
            match = DEFERRED_NOTES_RE.fullmatch(notes)
            if match is None:
                problems.append(
                    f"{alias}: DEFERRED Notes must name 'failed route' and "
                    "'attempt date' (YYYY-MM-DD)"
                )
            else:
                try:
                    date.fromisoformat(match.group("attempt_date"))
                except ValueError:
                    problems.append(
                        f"{alias}: DEFERRED Notes attempt date is not a valid date"
                    )

    for alias in sorted(set(entries) - set(wanted)):
        problems.append(f"{alias}: row present but not in --aliases")

    if problems:
        print("candidate matrix is INCOMPLETE:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print(
        f"candidate matrix complete: {len(wanted)} rows x "
        f"{len(REQUIRED_FIELDS)} fields, snapshot {snapshot}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
