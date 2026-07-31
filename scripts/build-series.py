#!/usr/bin/env python3
"""Turn the verbatim upstream/ patches into a git-am-able mailbox series.

Why this exists
---------------
upstream/*.patch are raw ``diff -ruN aa/ bb/`` output. They carry no mail headers,
so ``git am`` rejects them before it ever looks at a hunk -- the upstream README's
``git am /path/to/patches/*.patch`` instruction has never worked. Two of them also
carry macOS ``.DS_Store`` "Binary files ... differ" stanzas, which ``git apply``
refuses ("cannot apply binary patch ... without full index line") even once headers
exist.

On top of that, upstream targeted v6.19-rc8 and we target the tag in kernel-pin.env,
so a few context anchors have drifted. Those are re-anchored from an explicit,
reviewable table (rebase/<tag>.rules) -- never inline in this file.

Guarantees
----------
* Deterministic: same inputs -> byte-identical output. ``--check`` relies on it.
* Behaviour-preserving by construction: a rule may only touch a CONTEXT line.
  Attempting to rewrite a '+'/'-' line raises. scripts/verify-payload-parity.py
  proves the result independently.
* Upstream numbering (0001/0002/0003/0005, gap at 0004) is never renumbered.

Usage
-----
    scripts/build-series.py            regenerate patches/
    scripts/build-series.py --check    rebuild into a temp dir and diff; non-zero
                                       exit if patches/ is stale or hand-edited
"""

from __future__ import annotations

import argparse
import filecmp
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPSTREAM_DIR = ROOT / "upstream"
PATCHES_DIR = ROOT / "patches"
REBASE_DIR = ROOT / "rebase"
PIN_FILE = ROOT / "kernel-pin.env"

# Upstream's slot count. 0004 was never published; we keep the gap so our files
# line up 1:1 with theirs, hence Subject ordinals 1/5, 2/5, 3/5, 5/5.
SERIES_TOTAL = 5

DS_STORE_RE = re.compile(r"^Binary files .*\.DS_Store .* differ$")
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")


@dataclass(frozen=True)
class Patch:
    """One member of the series."""

    filename: str
    ordinal: int
    subject: str
    provenance: str  # upstream commit that last touched `filename`
    author: str
    date: str


SERIES: tuple[Patch, ...] = (
    Patch(
        filename="0001-rockchip-rk3588-vepu580-encoder-support-v3.patch",
        ordinal=1,
        subject=(
            "rockchip: rk3588: add VEPU580 (RKVENC v2) "
            "H.265/H.264/JPEG encoder support"
        ),
        provenance="09595583f3ffadd3d790a20ead392434e0e46728",
        author="Ross Cawston <rcawston@users.noreply.github.com>",
        date="Mon, 9 Feb 2026 20:42:16 -0800",
    ),
    Patch(
        filename="0002-rockchip-rk3588-hdmirx-edid-fix-v1.patch",
        ordinal=2,
        subject="media: synopsys: hdmirx: make a written EDID visible to the HDMI source",
        provenance="8478ca74ad2f340feb7f443acbb669292497cf3e",
        author="Ross Cawston <rcawston@users.noreply.github.com>",
        date="Mon, 9 Feb 2026 12:10:15 -0800",
    ),
    Patch(
        filename="0003-rockchip-rk3588-hdmirx-plugout-fix-v1.patch",
        ordinal=3,
        subject="media: synopsys: hdmirx: fix buffer overflow on repeated HDMI-RX replug",
        provenance="90b3a5c579ffb0ac164e4cea7163228a864ef0c4",
        author="Ross Cawston <rcawston@users.noreply.github.com>",
        date="Mon, 9 Feb 2026 14:35:17 -0800",
    ),
    Patch(
        filename="0005-rockchip-rk3588-hdmirx-audio.patch",
        ordinal=5,
        subject="media: synopsys: hdmirx: add HDMI-RX audio capture support",
        provenance="e13a311d8ee5e8ed92ec3d4a57c21f766c61d660",
        author="Ross Cawston <rcawston@users.noreply.github.com>",
        date="Wed, 1 Jul 2026 14:19:29 -0700",
    ),
)


class RebaseError(RuntimeError):
    """A rule could not be applied safely. Never resolved silently."""


def read_pin() -> dict[str, str]:
    """Parse the shell-ish kernel-pin.env into a plain dict."""
    pin: dict[str, str] = {}
    for raw in PIN_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        pin[key.strip()] = value.strip().strip('"')
    return pin


@dataclass(frozen=True)
class Rule:
    patch: str
    op: str
    anchor: str
    payload: str
    lineno: int


def load_rules(tag: str) -> list[Rule]:
    """Load rebase/<tag>.rules. Absent file means the series needs no re-anchoring."""
    path = REBASE_DIR / f"{tag}.rules"
    if not path.exists():
        return []

    rules: list[Rule] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split("|")
        if len(fields) != 4:
            raise RebaseError(f"{path}:{lineno}: expected 4 '|'-separated fields")
        patch, op, anchor, payload = fields
        if op not in {"replace", "insert-before"}:
            raise RebaseError(f"{path}:{lineno}: unknown op {op!r}")
        rules.append(
            Rule(
                patch=patch,
                op=op,
                # Rules are written with literal \t for readability.
                anchor=anchor.replace("\\t", "\t"),
                payload=payload.replace("\\t", "\t"),
                lineno=lineno,
            )
        )
    return rules


def _hunk_bounds(lines: list[str], idx: int) -> tuple[int, int]:
    """Return [start, end) of the hunk body containing body-line index `idx`."""
    start = idx
    while start >= 0 and not HUNK_RE.match(lines[start]):
        start -= 1
    if start < 0:
        raise RebaseError("matched line is not inside a hunk")
    end = start + 1
    while end < len(lines) and not (
        HUNK_RE.match(lines[end])
        or lines[end].startswith("diff -ruN ")
        or lines[end].startswith("--- ")
        or lines[end].startswith("+++ ")
    ):
        end += 1
    return start, end


def _bump_hunk_header(header: str, delta: int) -> str:
    """Widen a @@ header's old and new counts by `delta`."""
    m = HUNK_RE.match(header)
    if not m:
        raise RebaseError(f"not a hunk header: {header!r}")
    old_start, old_len, new_start, new_len, trailer = m.groups()
    old_count = int(old_len) if old_len is not None else 1
    new_count = int(new_len) if new_len is not None else 1
    return (
        f"@@ -{old_start},{old_count + delta} "
        f"+{new_start},{new_count + delta} @@{trailer}"
    )


def apply_rule(lines: list[str], rule: Rule) -> list[str]:
    """Apply one context-only rule. Raises rather than guessing."""
    target = " " + rule.anchor  # context lines carry a leading space in a diff
    hits = [i for i, line in enumerate(lines) if line == target]

    if not hits:
        # Also look for the anchor as a '+'/'-' line, to give a precise diagnosis
        # instead of a bare "not found".
        for i, line in enumerate(lines):
            if line[1:] == rule.anchor and line[:1] in ("+", "-"):
                raise RebaseError(
                    f"rule at rebase line {rule.lineno} matched a "
                    f"{'added' if line[0] == '+' else 'removed'} line, not context. "
                    "Rules may only re-anchor context; this would change behaviour."
                )
        raise RebaseError(
            f"rule at rebase line {rule.lineno}: anchor not found in {rule.patch}"
        )
    if len(hits) > 1:
        raise RebaseError(
            f"rule at rebase line {rule.lineno}: anchor matched {len(hits)} times "
            f"in {rule.patch}; it must be unambiguous"
        )

    idx = hits[0]
    out = list(lines)

    if rule.op == "replace":
        out[idx] = " " + rule.payload
        return out

    # insert-before: one extra context line widens both sides of the hunk by 1.
    hunk_start, _ = _hunk_bounds(out, idx)
    out.insert(idx, " " + rule.payload)
    out[hunk_start] = _bump_hunk_header(out[hunk_start], 1)
    return out


def build_patch(patch: Patch, rules: list[Rule], pin: dict[str, str]) -> str:
    src = UPSTREAM_DIR / patch.filename
    if not src.is_file():
        raise RebaseError(f"missing upstream patch: {src}")

    body = src.read_text(encoding="utf-8", errors="surrogateescape").splitlines()

    dropped = sum(1 for line in body if DS_STORE_RE.match(line))
    body = [line for line in body if not DS_STORE_RE.match(line)]

    applied = [r for r in rules if r.patch == patch.filename]
    for rule in applied:
        body = apply_rule(body, rule)

    upstream_repo = pin["UPSTREAM_PATCHES_REPO"]
    upstream_rev = pin["UPSTREAM_PATCHES_REV"]
    tag = pin["KERNEL_TAG"]
    tested = pin["UPSTREAM_TESTED_KERNEL"]

    header: list[str] = [
        # mbox delimiter. The hex is the upstream commit that last touched this
        # file, so provenance is machine-readable rather than decorative.
        f"From {patch.provenance} Mon Sep 17 00:00:00 2001",
        f"From: {patch.author}",
        f"Date: {patch.date}",
        f"Subject: [PATCH {patch.ordinal}/{SERIES_TOTAL}] {patch.subject}",
        "",
        f"Imported from {upstream_repo}",
        f"at {upstream_rev}, file {patch.filename}.",
        "",
        "Authored by Ross Cawston. This CeraLive copy re-packages the file as a git",
        "mailbox so it can be applied with `git am`. Every added and removed line is",
        "byte-identical to upstream's; scripts/verify-payload-parity.py enforces that.",
        "",
    ]

    if dropped:
        header += [
            f'Dropped {dropped} payload-free "Binary files .../.DS_Store ... differ"',
            "stanza(s) that macOS left in the original `diff -ruN` output. They carry",
            "no data, and git apply refuses a binary stanza with no index line.",
            "",
        ]

    if applied:
        header += [
            f"Re-anchored for {tag} (upstream developed this against {tested}):",
        ]
        header += [
            f"  - {'replaced' if r.op == 'replace' else 'restored'} context line "
            f"`{r.anchor.strip()}`"
            for r in applied
        ]
        header += [
            "Context lines only -- see rebase/%s.rules and docs/REBASE-%s.md for the"
            % (tag, tag),
            "hunk-by-hunk ledger.",
            "",
        ]

    header += [
        "NOT upstream-bound: this is a CeraLive-maintained adaptation, not a submission",
        f"to {upstream_repo.rsplit('/', 1)[-1]}. No Signed-off-by is added, because none",
        "was given upstream and inventing one would misattribute a DCO assertion.",
        "",
        "---",
    ]

    return "\n".join(header + body) + "\n"


def write_series(out_dir: Path, pin: dict[str, str]) -> None:
    rules = load_rules(pin["KERNEL_TAG"])

    known = {p.filename for p in SERIES}
    for rule in rules:
        if rule.patch not in known:
            raise RebaseError(
                f"rebase rule at line {rule.lineno} names unknown patch {rule.patch!r}"
            )

    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("*.patch"):
        stale.unlink()
    (out_dir / "series").unlink(missing_ok=True)

    for patch in SERIES:
        (out_dir / patch.filename).write_text(
            build_patch(patch, rules, pin), encoding="utf-8", errors="surrogateescape"
        )

    series_lines = [
        "# git-am order for the CeraLive RK3588 series.",
        "# Upstream numbering is preserved verbatim -- 0004 was never published,",
        "# so the gap is intentional. Do not renumber to close it.",
        f"# Target kernel: {pin['KERNEL_TAG']} ({pin['KERNEL_COMMIT']})",
        *(p.filename for p in SERIES),
    ]
    (out_dir / "series").write_text("\n".join(series_lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify patches/ matches what this script would generate",
    )
    args = parser.parse_args()

    pin = read_pin()

    if not args.check:
        write_series(PATCHES_DIR, pin)
        print(f"wrote {len(SERIES)} patches + series to {PATCHES_DIR}")
        return 0

    with tempfile.TemporaryDirectory() as tmp:
        expected = Path(tmp) / "patches"
        write_series(expected, pin)

        names = sorted({p.name for p in expected.iterdir()})
        match, mismatch, errors = filecmp.cmpfiles(
            PATCHES_DIR, expected, names, shallow=False
        )
        if mismatch or errors:
            print("patches/ is STALE or hand-edited.", file=sys.stderr)
            for name in sorted(mismatch):
                print(f"  differs: {name}", file=sys.stderr)
            for name in sorted(errors):
                print(f"  missing: {name}", file=sys.stderr)
            print("Re-run scripts/build-series.py.", file=sys.stderr)
            return 1

        extra = sorted({p.name for p in PATCHES_DIR.iterdir()} - set(names))
        if extra:
            print(f"unexpected files in patches/: {extra}", file=sys.stderr)
            return 1

        print(f"patches/ is in sync ({len(match)} files).")
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RebaseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
