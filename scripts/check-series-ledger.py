#!/usr/bin/env python3
"""Hold the series, the generated patches and the status ledger to one story.

``build-series.py --check`` proves ``patches/`` is what the generator produces.
``verify-payload-parity.py`` proves it changes nothing its source lane did not.
Neither reads ``docs/UPSTREAM-STATUS.md``, so a patch could be imported, applied
and shipped while its status row said something else entirely -- or said nothing.
That gap is what this checker closes: membership, ordinals, subjects, provenance
variant, the STATUS row set, and declared dependency order, compared exactly.

It imports SERIES from build-series.py on purpose. Its independent axis is the
documentation, not a second re-derivation of the generator -- that job belongs to
verify-payload-parity.py and must stay separate from this one.

Usage:
    scripts/check-series-ledger.py
    scripts/check-series-ledger.py --require-before U2:U1
    scripts/check-series-ledger.py --exact docs/UPSTREAM-STATUS.md
    scripts/check-series-ledger.py --self-test

Exit: 0 consistent, 1 inconsistent, 2 misuse.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATUS_DOC = ROOT / "docs" / "UPSTREAM-STATUS.md"

MEMBER_ROW_RE = re.compile(r"^\|\s*`(?P<ordinal>\d{4})`")
CURRENT_SERIES_BEGIN = "<!-- current-series: begin -->"
CURRENT_SERIES_END = "<!-- current-series: end -->"
SUBJECT_RE = re.compile(r"^Subject: \[PATCH (?P<ordinal>\d+)/(?P<total>\d+)\] (?P<rest>.*)$")
FORBIDDEN_MERGED_MARKER_RE = re.compile(r"^commit [0-9a-f]{40} upstream\.$", re.MULTILINE)
NULL_OID_RE = re.compile(r"\b0{40}\b")
SHA1_ANYWHERE_RE = re.compile(r"^From ([0-9a-f]{40}) ")

ALIAS_HEADING_RE = re.compile(r"^####\s+(?P<alias>[A-Z][0-9]+)\b")
FIELD_RE = re.compile(r"^-\s+(?P<key>[A-Za-z][A-Za-z0-9 /()-]*):\s*(?P<value>.+?)\s*$")
LORE_ID_RE = re.compile(r"lore `(?P<msgid>[^`]+)`")


def load_build_series():
    spec = importlib.util.spec_from_file_location(
        "ceralive_build_series", ROOT / "scripts" / "build-series.py"
    )
    if spec is None or spec.loader is None:
        raise SystemExit("error: cannot load scripts/build-series.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def status_member_ordinals(text: str) -> list[str]:
    if CURRENT_SERIES_BEGIN in text and CURRENT_SERIES_END in text:
        text = text.split(CURRENT_SERIES_BEGIN, 1)[1].split(CURRENT_SERIES_END, 1)[0]
    return [
        match.group("ordinal")
        for line in text.splitlines()
        if (match := MEMBER_ROW_RE.match(line.strip()))
    ]


def parse_matrix(text: str) -> dict[str, dict[str, str]]:
    if "<!-- candidate-matrix: begin -->" not in text:
        return {}
    body = text.split("<!-- candidate-matrix: begin -->", 1)[1]
    body = body.split("<!-- candidate-matrix: end -->", 1)[0]
    entries: dict[str, dict[str, str]] = {}
    current: str | None = None
    for raw in body.splitlines():
        line = raw.strip()
        heading = ALIAS_HEADING_RE.match(line)
        if heading:
            current = heading.group("alias")
            entries.setdefault(current, {})
            continue
        field = FIELD_RE.match(line)
        if field and current is not None:
            entries[current].setdefault(field.group("key").strip(), field.group("value"))
    return entries


def check_members(bs, problems: list[str]) -> None:
    ordinals = [patch.ordinal for patch in bs.SERIES]
    if ordinals != sorted(ordinals):
        problems.append(f"SERIES ordinals are out of order: {ordinals}")
    if len(set(ordinals)) != len(ordinals):
        problems.append(f"SERIES reuses an ordinal: {ordinals}")
    if 4 in ordinals:
        problems.append("ordinal 0004 is the intentional gap and must stay unused")

    series_file = ROOT / "patches" / "series"
    listed = [
        line.strip()
        for line in series_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    expected = [patch.filename for patch in bs.SERIES]
    if listed != expected:
        problems.append(
            "patches/series membership or order differs from SERIES:\n"
            f"      series: {listed}\n      SERIES: {expected}"
        )

    for patch in bs.SERIES:
        generated = ROOT / "patches" / patch.filename
        source = ROOT / patch.origin / patch.filename
        if not source.is_file():
            problems.append(f"{patch.filename}: missing source {patch.origin}/")
        if not generated.is_file():
            problems.append(f"{patch.filename}: missing generated patches/ counterpart")
            continue
        text = generated.read_text(encoding="utf-8", errors="surrogateescape")
        header = text.split("\n---\n", 1)[0]
        subject = next(
            (line for line in header.splitlines() if line.startswith("Subject: ")), ""
        )
        want = (
            f"Subject: [PATCH {patch.ordinal}/{bs.SERIES_TOTAL}] {patch.subject}"
        )
        if subject != want:
            problems.append(
                f"{patch.filename}: subject line is\n      {subject!r}\n"
                f"      expected {want!r}"
            )
        check_provenance(bs, patch, header, problems)


def check_provenance(bs, patch, header: str, problems: list[str]) -> None:
    where = patch.filename
    delimiter = header.splitlines()[0] if header else ""
    sha_delim = SHA1_ANYWHERE_RE.match(delimiter)

    if patch.origin == bs.ISLAND:
        if not isinstance(patch.provenance, bs.Island):
            problems.append(f"{where}: island provenance is not an Island variant")
            return
        if sha_delim:
            problems.append(
                f"{where}: island delimiter claims kernel commit {sha_delim.group(1)}"
            )
        if FORBIDDEN_MERGED_MARKER_RE.search(header):
            problems.append(f"{where}: island header claims an upstream commit")
        if NULL_OID_RE.search(header):
            problems.append(f"{where}: island header carries NULL_OID")
        identity = (
            "Generated from CeraLive rk3588-media-island "
            f"{patch.provenance.tag} ({patch.provenance.commit})."
        )
        if identity not in header:
            problems.append(f"{where}: island header omits {identity!r}")
        if patch.provenance.asset_sha256 not in header:
            problems.append(f"{where}: island header omits its asset sha256")
        return

    if patch.origin == bs.BACKPORTS and patch.lore is not None:
        if patch.provenance != bs.LORE_POSTING:
            problems.append(f"{where}: lore provenance must be {bs.LORE_POSTING!r}")
        if sha_delim:
            problems.append(
                f"{where}: the mbox delimiter carries a 40-hex object id "
                f"({sha_delim.group(1)}); an unmerged posting has no such identity"
            )
        if FORBIDDEN_MERGED_MARKER_RE.search(header):
            problems.append(
                f"{where}: the header claims `commit <sha> upstream.`, which is only "
                "true of a merged backport"
            )
        if NULL_OID_RE.search(header):
            problems.append(f"{where}: the header carries NULL_OID")
        if "ALREADY upstream" in header:
            problems.append(f"{where}: the header claims ALREADY upstream")
        if f"Backport of unmerged {patch.lore.revision} posting." not in header:
            problems.append(
                f"{where}: the header does not state 'Backport of unmerged "
                f"{patch.lore.revision} posting.'"
            )
        for digest in (
            patch.lore.thread_compressed_sha256,
            patch.lore.thread_mbox_sha256,
            patch.lore.canonical_patch_sha256,
        ):
            if digest not in header:
                problems.append(f"{where}: the header omits digest {digest}")
        return

    if patch.origin == bs.BACKPORTS:
        if not sha_delim or sha_delim.group(1) == bs.NULL_OID:
            problems.append(
                f"{where}: a merged backport's delimiter must be its 40-hex commit"
            )
        if not FORBIDDEN_MERGED_MARKER_RE.search(header):
            problems.append(
                f"{where}: a merged backport must carry the `commit <sha> upstream.` "
                "marker"
            )
        return

    if "Backport of unmerged" in header:
        problems.append(f"{where}: a non-backports lane must not claim a lore posting")


def check_status(bs, text: str, exact: bool, problems: list[str]) -> None:
    rows = status_member_ordinals(text)
    if len(set(rows)) != len(rows):
        problems.append(f"UPSTREAM-STATUS.md has a duplicate member row: {rows}")
    carried = [f"{patch.ordinal:04d}" for patch in bs.SERIES]
    missing = [ordinal for ordinal in carried if ordinal not in rows]
    stale = [ordinal for ordinal in rows if ordinal not in carried]
    for ordinal in missing:
        problems.append(f"UPSTREAM-STATUS.md has no row for carried patch {ordinal}")
    for ordinal in stale:
        problems.append(
            f"UPSTREAM-STATUS.md row {ordinal} is stale; the series does not carry it"
        )
    if exact and rows != carried:
        problems.append(
            "UPSTREAM-STATUS.md member rows are not in series order:\n"
            f"      rows:   {rows}\n      series: {carried}"
        )


def alias_positions(bs, matrix: dict[str, dict[str, str]]) -> dict[str, int]:
    carried = {}
    for index, patch in enumerate(bs.SERIES):
        if patch.lore is not None:
            carried[patch.lore.lore_msgid] = index
    positions: dict[str, int] = {}
    for alias, fields in matrix.items():
        found = LORE_ID_RE.search(fields.get("Identity", ""))
        if found and found.group("msgid") in carried:
            positions[alias] = carried[found.group("msgid")]
    return positions


def check_require_before(
    bs,
    matrix: dict[str, dict[str, str]],
    requirements: list[str],
    problems: list[str],
) -> None:
    positions = alias_positions(bs, matrix)
    for requirement in requirements:
        if requirement.count(":") != 1:
            problems.append(f"--require-before {requirement!r} is not ALIAS:ALIAS")
            continue
        first, second = requirement.split(":")
        for alias in (first, second):
            if alias not in matrix:
                problems.append(
                    f"--require-before {requirement}: {alias} has no matrix row, so "
                    "its position cannot be asserted either way"
                )
        if first not in matrix or second not in matrix:
            continue
        both_carried = first in positions and second in positions
        if both_carried:
            if positions[first] >= positions[second]:
                problems.append(
                    f"--require-before {requirement}: {first} is at series position "
                    f"{positions[first]}, {second} at {positions[second]}; the "
                    "prerequisite must come first"
                )
            continue
        # Not carried is only acceptable when the matrix says so out loud. An
        # absent candidate with no recorded disposition is a gap, not a decision.
        for alias in (first, second):
            if alias in positions:
                continue
            disposition = matrix[alias].get("Disposition", "")
            if disposition in ("", "IN"):
                problems.append(
                    f"--require-before {requirement}: {alias} is not carried but its "
                    f"matrix disposition is {disposition!r}; an IN candidate must be "
                    "in the series"
                )


SELF_TEST_CARRIED = ["0001", "0005", "0007"]

SELF_TEST_CASES = (
    ("complete", "| `0001` a |\n| `0005` b |\n| `0007` c |\n", True),
    ("missing", "| `0001` a |\n| `0007` c |\n", False),
    ("duplicate", "| `0001` a |\n| `0005` b |\n| `0005` b |\n| `0007` c |\n", False),
    ("stale", "| `0001` a |\n| `0005` b |\n| `0007` c |\n| `0099` gone |\n", False),
    ("out-of-order", "| `0005` b |\n| `0001` a |\n| `0007` c |\n", False),
)


class _FakePatch:
    def __init__(self, ordinal: int) -> None:
        self.ordinal = ordinal


class _FakeSeries:
    def __init__(self) -> None:
        self.SERIES = [_FakePatch(int(o)) for o in SELF_TEST_CARRIED]


def self_test() -> int:
    failures = 0
    for name, table, should_pass in SELF_TEST_CASES:
        problems: list[str] = []
        check_status(_FakeSeries(), table, exact=True, problems=problems)
        passed = not problems
        verdict = "OK  " if passed == should_pass else "FAIL"
        if passed != should_pass:
            failures += 1
        print(f"  {verdict} {name}: {'accepted' if passed else 'rejected'}")
    if failures:
        print(f"self-test: {failures} case(s) behaved wrongly", file=sys.stderr)
        return 1
    print(f"self-test: {len(SELF_TEST_CASES)} fixtures behave as specified")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-before", action="append", default=[])
    parser.add_argument("--exact", type=Path, default=None)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    bs = load_build_series()
    problems: list[str] = []
    check_members(bs, problems)

    doc = args.exact if args.exact is not None else STATUS_DOC
    text = doc.read_text(encoding="utf-8")
    check_status(bs, text, exact=args.exact is not None, problems=problems)
    check_require_before(bs, parse_matrix(text), args.require_before, problems)

    if problems:
        print("series ledger is INCONSISTENT:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print(
        f"series ledger consistent: {len(bs.SERIES)} members, "
        f"{len(status_member_ordinals(text))} status rows, "
        f"{len(args.require_before)} order requirement(s)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
