#!/usr/bin/env python3
"""Import an UNMERGED lore posting into backports/, without inventing an identity.

Why this exists
---------------
``backports/`` already carries merged commits: those have a 40-hex commit id, so
the generated mail header can honestly say ``commit <sha> upstream.``. A posting
that has NOT been merged has no such id, and the one thing this repository cannot
do is manufacture one. NULL_OID is 40 hex digits and would pass every shape test
while asserting "this came from the null commit", which is false; a parent SHA
asserts a merge that did not happen. So an unmerged posting gets a different
provenance variant entirely (see scripts/build-series.py :: LorePosting), and this
script is the only sanctioned way to produce its source bytes.

What "canonical" means here
---------------------------
The ONLY admissible source for an IN import is the archive's own compressed
thread mailbox::

    https://lore.kernel.org/all/<msgid>/t.mbox.gz

Patchwork's API and ``/r/<msgid>/raw`` are DISCOVERY instruments. They answer
"does this Message-ID resolve to anything at all", which is enough to justify an
OUT ``unfetchable-canonical-thread`` verdict -- and they are never allowed to
populate the compressed-thread domain, because a digest field named
``thread_compressed_sha256`` that was computed over something other than the
compressed thread is a lie with a checksum attached.

Hand-transcription is not a fallback. If the canonical archive cannot be fetched,
the candidate goes OUT; it does not get typed in by a human.

Determinism
-----------
Two imports of the same canonical thread produce byte-identical source files and a
byte-identical ledger. Every ordering is derived from the parsed ``[PATCH n/m]``
sequence, never from archive order, and the ledger is canonical JSON.

Usage
-----
    scripts/import-lore-series.py --msgid <id> --alias U2 --slug emmc-platform-data \\
        --expect-revision v2 --ordinal-start 10 --ledger evidence/U2.json

    scripts/import-lore-series.py --msgid <id> --alias U9 --probe-only \\
        --ledger evidence/U9-out.json      # records an OUT verdict with diagnostics

Exit: 0 success, 1 a screening REJECT (the candidate goes OUT), 2 misuse.
"""

from __future__ import annotations

import argparse
import email
import email.policy
import hashlib
import json
import mailbox
import re
import sys
import tempfile
import urllib.error
import urllib.request
import zlib
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LORE_ARCHIVE = "https://lore.kernel.org"
PATCHWORK_API = "https://patchwork.kernel.org/api/patches/?msgid="

# Bounded decompression. A gzip member can expand without limit; the archive's
# real threads are kilobytes, so a ceiling this generous still refuses a bomb.
MAX_DECOMPRESSED_BYTES = 32 * 1024 * 1024
MAX_MESSAGE_COUNT = 512
DECOMPRESS_CHUNK = 64 * 1024

USER_AGENT = "ceralive-rk3588-kernel-patches/import-lore-series"
HTTP_TIMEOUT = 60

SUBJECT_TAG_RE = re.compile(r"^\s*\[(?P<tags>[^\]]*)\]\s*(?P<title>.+?)\s*$")
REVISION_RE = re.compile(r"^v(\d+)$", re.IGNORECASE)
SEQUENCE_RE = re.compile(r"^(\d+)/(\d+)$")
MBOXRD_QUOTED_FROM_RE = re.compile(r"^>(>*From )", re.MULTILINE)
LIST_FOOTER_SEPARATOR_RE = re.compile(r"^(?:_{10,}|-- )$")
LIST_FOOTER_HINT_RE = re.compile(r"\bmailing list\b|^https?://lists\.", re.IGNORECASE)
LIST_FOOTER_WINDOW = 12

# The `/all/` archive merges one posting's per-list copies into a single thread,
# so the same message arrives several times wearing different transport headers,
# different Content-Transfer-Encoding, and a different mailman footer. Comparing
# raw bytes therefore reports corruption on every ordinary message. What actually
# has to agree is the AUTHORED message, so canonical form is exactly these three
# author-supplied headers plus the decoded body -- and nothing a list added.
#
# From: is deliberately absent. Lists rewrite it: b4's relay replaces the author
# with `devnull+...@kernel.org` on some copies and not others, and DMARC munging
# does the same on others again. Including it would make every relayed series
# look corrupt, so the observed values are recorded beside the digest instead of
# inside it.
CANONICAL_HEADERS = ("Message-ID", "Subject", "Date")
RELAY_FROM_RE = re.compile(r"devnull\+|via .*Relay", re.IGNORECASE)
DIFF_START_RE = re.compile(r"^diff --git ")
DIFF_FALLBACK_RE = re.compile(r"^--- (a/|/dev/null|[^\s]+\t)")
GIT_SIGNATURE_RE = re.compile(r"^-- $")
DIFF_PAYLOAD_RE = re.compile(r"^(diff --git |@@ |\+\+\+ |--- [ab]/|Binary files )")
B4_TRAILER_RE = re.compile(r"^(base-commit|change-id|prerequisite-[a-z-]+):\s")


class LoreImportError(RuntimeError):
    """A screening refusal. Carries the error class the matrix records."""

    def __init__(self, error_class: str, detail: str) -> None:
        super().__init__(f"{error_class}: {detail}")
        self.error_class = error_class
        self.detail = detail


@dataclass(frozen=True)
class CanonicalMessage:
    """One deduplicated, mboxrd-unescaped message from the canonical thread."""

    msgid: str
    subject: str
    author: str
    date: str
    revision: str
    sequence: int
    total: int
    is_cover: bool
    canonical_bytes: bytes
    diff_text: str
    review_tags: tuple[str, ...]

    @property
    def canonical_sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes).hexdigest()

    @property
    def diff_sha256(self) -> str:
        return hashlib.sha256(self.diff_text.encode("utf-8")).hexdigest()


@dataclass
class ThreadFetch:
    """Exactly what came back from the canonical archive, and its digests."""

    url: str
    compressed: bytes
    mbox: bytes
    diagnostics: dict[str, str] = field(default_factory=dict)

    @property
    def compressed_sha256(self) -> str:
        return hashlib.sha256(self.compressed).hexdigest()

    @property
    def mbox_sha256(self) -> str:
        return hashlib.sha256(self.mbox).hexdigest()


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------


def thread_url(msgid: str) -> str:
    return f"{LORE_ARCHIVE}/all/{msgid}/t.mbox.gz"


def http_get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:  # noqa: S310
        if response.status != 200:
            raise LoreImportError(
                "unfetchable-canonical-thread", f"{url} returned {response.status}"
            )
        return response.read()


def decompress_bounded(
    raw: bytes,
    max_bytes: int = MAX_DECOMPRESSED_BYTES,
) -> bytes:
    """gunzip with a hard output ceiling.

    zlib.decompress() would happily materialise a petabyte from a few kilobytes.
    Feeding the stream in fixed chunks and checking the running total after each
    one is what makes the ceiling real rather than advisory.
    """
    engine = zlib.decompressobj(wbits=16 + zlib.MAX_WBITS)
    out = bytearray()
    for offset in range(0, len(raw), DECOMPRESS_CHUNK):
        try:
            out += engine.decompress(raw[offset : offset + DECOMPRESS_CHUNK], max_bytes)
        except zlib.error as exc:
            raise LoreImportError(
                "unfetchable-canonical-thread", f"not a gzip stream: {exc}"
            ) from exc
        if len(out) > max_bytes or engine.unconsumed_tail:
            raise LoreImportError(
                "decompression-limit-exceeded",
                f"thread expands past the {max_bytes}-byte ceiling",
            )
    out += engine.flush()
    if len(out) > max_bytes:
        raise LoreImportError(
            "decompression-limit-exceeded",
            f"thread expands past the {max_bytes}-byte ceiling",
        )
    if not out:
        raise LoreImportError("unfetchable-canonical-thread", "empty thread mailbox")
    return bytes(out)


def discovery_probe(msgid: str) -> dict[str, str]:
    """Diagnostics only. NEVER a source of patch bytes.

    These two endpoints exist here for one purpose: to say, in an OUT verdict,
    whether the Message-ID resolves anywhere at all -- "the archive is down" and
    "this Message-ID does not exist" are different findings and both are useful.
    Neither result may be promoted into a thread digest or a patch body.
    """
    probes = {
        "patchwork_api": f"{PATCHWORK_API}{msgid}",
        "lore_raw": f"{LORE_ARCHIVE}/r/{msgid}/raw",
    }
    results: dict[str, str] = {}
    for name, url in sorted(probes.items()):
        try:
            body = http_get(url)
        except (LoreImportError, urllib.error.URLError, OSError) as exc:
            results[name] = f"unavailable ({type(exc).__name__})"
            continue
        results[name] = f"resolved ({len(body)} bytes, DIAGNOSTIC ONLY)"
    return results


def fetch_thread(
    msgid: str,
    *,
    thread_file: Path | None,
    allow_network: bool,
) -> ThreadFetch:
    url = thread_url(msgid)
    if thread_file is not None:
        compressed = thread_file.read_bytes()
    elif not allow_network:
        raise LoreImportError(
            "unfetchable-canonical-thread",
            "--no-network was requested and no --thread-file was supplied",
        )
    else:
        try:
            compressed = http_get(url)
        except LoreImportError:
            raise
        except (urllib.error.URLError, OSError) as exc:
            raise LoreImportError(
                "unfetchable-canonical-thread", f"{url}: {exc}"
            ) from exc
    return ThreadFetch(url=url, compressed=compressed, mbox=decompress_bounded(compressed))


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------


def normalise_msgid(raw: str | None) -> str:
    """Fold a Message-ID header down to the form a lore URL uses.

    Headers fold across lines and archives re-wrap them, so two copies of the
    same message can differ in whitespace alone. Angle brackets are equally
    decorative. Case is NOT folded: the local part is case-sensitive.
    """
    if raw is None:
        raise LoreImportError("missing-message-id", "a thread message has no Message-ID")
    collapsed = "".join(raw.split())
    if collapsed.startswith("<") and collapsed.endswith(">"):
        collapsed = collapsed[1:-1]
    if not collapsed:
        raise LoreImportError("missing-message-id", "empty Message-ID header")
    return collapsed


def unescape_mboxrd(text: str) -> str:
    """``>From `` -> ``From ``. One level, exactly as mboxrd defines it."""
    return MBOXRD_QUOTED_FROM_RE.sub(r"\1", text)


def strip_list_footer(text: str) -> str:
    """Drop a trailing mailman footer, which is the list's text and not the author's.

    Two shapes are in use across the lists this project reads -- an underscore
    rule and a plain ``-- `` signature marker -- and the second one collides with
    git's own trailing ``-- \\n<version>``. Anchoring on the "mailing list" line
    and only then walking back to the nearest separator is what tells them apart.
    """
    lines = text.rstrip("\n").split("\n")
    window = max(0, len(lines) - LIST_FOOTER_WINDOW)
    tail = [line for line in lines[window:] if not line.startswith(">")]
    if not any(LIST_FOOTER_HINT_RE.search(line) for line in tail):
        return text
    for index in range(len(lines) - 1, window - 1, -1):
        line = lines[index]
        if line.startswith(">") or not LIST_FOOTER_SEPARATOR_RE.match(line):
            continue
        if not any(LIST_FOOTER_HINT_RE.search(rest) for rest in lines[index + 1 :]):
            continue
        return "\n".join(lines[:index]).rstrip("\n")
    return text


def canonicalise(raw: bytes) -> bytes:
    """The authored message, reduced to the form every archived copy agrees on."""
    message = email.message_from_bytes(raw, policy=email.policy.compat32)
    head = [
        f"{name}: {unfold_subject(message.get(name))}"
        for name in CANONICAL_HEADERS
        if message.get(name) is not None
    ]
    body = strip_list_footer(message_text(raw)).rstrip("\n")
    document = "\n".join(head) + "\n\n" + body + "\n"
    return document.encode("utf-8", errors="surrogateescape")


def unfold_subject(raw: str | None) -> str:
    if raw is None:
        return ""
    return " ".join(str(raw).split())


def parse_subject_tag(subject: str) -> tuple[str, int | None, int | None, str] | None:
    """``[PATCH v3 2/10] title`` -> (revision, seq, total, title).

    Returns None when the subject is not a patch posting at all -- a reply, an
    announcement, a bot notification. A reviewer's inline diff in a ``Re:`` is
    exactly the thing that must not be mistaken for a series member.
    """
    if subject.lower().startswith("re:"):
        return None
    match = SUBJECT_TAG_RE.match(subject)
    if not match:
        return None
    tokens = match.group("tags").replace(",", " ").split()
    if not any(token.upper() == "PATCH" for token in tokens):
        return None
    revision = "v1"
    sequence: int | None = None
    total: int | None = None
    for token in tokens:
        rev = REVISION_RE.match(token)
        if rev:
            revision = f"v{int(rev.group(1))}"
            continue
        seq = SEQUENCE_RE.match(token)
        if seq:
            sequence, total = int(seq.group(1)), int(seq.group(2))
    return revision, sequence, total, match.group("title")


def message_text(raw: bytes) -> str:
    message = email.message_from_bytes(raw, policy=email.policy.compat32)
    if message.is_multipart():
        parts = []
        for part in message.walk():
            if part.get_content_maintype() != "text":
                continue
            payload = part.get_payload(decode=True)
            if payload:
                parts.append(payload.decode("utf-8", errors="surrogateescape"))
        text = "\n".join(parts)
    else:
        payload = message.get_payload(decode=True)
        text = (
            payload.decode("utf-8", errors="surrogateescape")
            if payload
            else str(message.get_payload())
        )
    return unescape_mboxrd(text.replace("\r\n", "\n").replace("\r", "\n"))


def extract_diff(text: str) -> str:
    """The patch body, in the shape the source lanes store: diff and nothing else.

    The lane file is the source of record and build-series.py prepends the mail
    header itself, so a stored message header would be duplicated. The commit
    message is not lost -- it travels in the generated header's note and in the
    canonical mail archived beside the patch.
    """
    lines = text.split("\n")
    start = None
    for index, line in enumerate(lines):
        if DIFF_START_RE.match(line) or DIFF_FALLBACK_RE.match(line):
            start = index
            break
    if start is None:
        return ""
    end = len(lines)
    for index in range(len(lines) - 1, start, -1):
        if GIT_SIGNATURE_RE.match(lines[index]):
            end = index
            break
    # b4 appends a `---` + base-commit/change-id trailer AFTER the diff, which is
    # metadata about the posting rather than part of the payload.
    for index in range(start, end):
        if lines[index] != "---":
            continue
        rest = lines[index + 1 : end]
        if any(DIFF_PAYLOAD_RE.match(line) for line in rest):
            continue
        if any(B4_TRAILER_RE.match(line) for line in rest):
            end = index
            break
    while end > start and (
        not lines[end - 1].strip() or B4_TRAILER_RE.match(lines[end - 1])
    ):
        end -= 1
    body = "\n".join(lines[start:end]).rstrip("\n")
    return body + "\n" if body else ""


REVIEW_TAG_RE = re.compile(
    r"^(Reviewed-by|Tested-by|Acked-by|Nacked-by|Signed-off-by|Reported-by):\s*(.+)$",
    re.MULTILINE,
)


def review_tags(text: str) -> tuple[str, ...]:
    return tuple(
        sorted({f"{name}: {value.strip()}" for name, value in REVIEW_TAG_RE.findall(text)})
    )


def split_thread(mbox_bytes: bytes) -> list[bytes]:
    """Split with the stdlib mbox reader, then hand back exact message bytes."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.mbox"
        path.write_bytes(mbox_bytes)
        box = mailbox.mbox(str(path))
        try:
            raws = [box.get_bytes(key) for key in box.iterkeys()]
        finally:
            box.close()
    if len(raws) > MAX_MESSAGE_COUNT:
        raise LoreImportError(
            "decompression-limit-exceeded",
            f"{len(raws)} messages exceeds the {MAX_MESSAGE_COUNT}-message ceiling",
        )
    return raws


@dataclass
class CanonicalCopy:
    canonical: bytes
    observed_from: set[str]


def preferred_author(observed: set[str]) -> str:
    """Pick the author the lists did not rewrite, deterministically."""
    direct = sorted(value for value in observed if not RELAY_FROM_RE.search(value))
    return direct[0] if direct else (sorted(observed)[0] if observed else "")


def deduplicate(raws: list[bytes]) -> dict[str, CanonicalCopy]:
    """Collapse the archive's repeats; refuse a Message-ID that means two things.

    lore's thread expansion returns each message more than once, and those copies
    are byte-identical -- collapsing them is deterministic and lossless. Two
    DIFFERENT bodies under one Message-ID is not a resend, it is corruption, and
    there is no defensible way to pick one.
    """
    seen: dict[str, CanonicalCopy] = {}
    for raw in raws:
        message = email.message_from_bytes(raw, policy=email.policy.compat32)
        msgid = normalise_msgid(message.get("Message-ID"))
        sender = unfold_subject(message.get("From"))
        canonical = canonicalise(raw)
        previous = seen.get(msgid)
        if previous is None:
            seen[msgid] = CanonicalCopy(canonical=canonical, observed_from={sender})
            continue
        if previous.canonical != canonical:
            raise LoreImportError(
                "duplicate-msgid-divergent-bytes",
                f"Message-ID {msgid} appears with two different canonical bodies",
            )
        previous.observed_from.add(sender)
    return seen


def build_messages(canonical: dict[str, CanonicalCopy]) -> list[CanonicalMessage]:
    messages: list[CanonicalMessage] = []
    for msgid, copy in canonical.items():
        raw = copy.canonical
        parsed = email.message_from_bytes(raw, policy=email.policy.compat32)
        subject = unfold_subject(parsed.get("Subject"))
        tag = parse_subject_tag(subject)
        if tag is None:
            continue
        revision, sequence, total, _title = tag
        text = message_text(raw)
        diff = extract_diff(text)
        is_cover = sequence == 0 or (sequence is None and not diff and total is None)
        if sequence is None:
            sequence, total = 1, 1
        if total is None:
            total = 1
        messages.append(
            CanonicalMessage(
                msgid=msgid,
                subject=subject,
                author=preferred_author(copy.observed_from),
                date=unfold_subject(parsed.get("Date")),
                revision=revision,
                sequence=sequence,
                total=total,
                is_cover=is_cover or sequence == 0,
                canonical_bytes=raw,
                diff_text=diff,
                review_tags=review_tags(text),
            )
        )
    return messages


def screen_series(
    messages: list[CanonicalMessage],
    expect_revision: str | None,
) -> list[CanonicalMessage]:
    """One coherent revision, a complete 1..N sequence, and no ambiguous diffs."""
    patches = [m for m in messages if not m.is_cover and m.diff_text]
    if not patches:
        raise LoreImportError(
            "no-diff-bearing-message", "the canonical thread carries no patch body"
        )

    revisions = sorted({m.revision for m in patches})
    if len(revisions) != 1:
        raise LoreImportError(
            "mixed-revision-thread",
            f"the thread carries {revisions}; a series import needs exactly one",
        )
    revision = revisions[0]
    if expect_revision is not None and revision != expect_revision:
        raise LoreImportError(
            "mixed-revision-thread",
            f"thread revision {revision} is not the expected {expect_revision}",
        )

    # A byte-identical diff under two DIFFERENT Message-IDs is never resolvable:
    # picking a survivor means picking which posting the series claims to carry.
    by_diff: dict[str, str] = {}
    for message in patches:
        first = by_diff.setdefault(message.diff_sha256, message.msgid)
        if first != message.msgid:
            raise LoreImportError(
                "duplicate-diff-distinct-msgid",
                f"identical diff bytes posted under {first} and {message.msgid}",
            )

    totals = sorted({m.total for m in patches})
    if len(totals) != 1:
        raise LoreImportError(
            "mixed-revision-thread", f"series totals disagree: {totals}"
        )
    total = totals[0]

    sequences = [m.sequence for m in patches]
    duplicates = sorted({s for s in sequences if sequences.count(s) > 1})
    if duplicates:
        raise LoreImportError(
            "duplicate-sequence", f"sequence number(s) {duplicates} posted twice"
        )
    missing = sorted(set(range(1, total + 1)) - set(sequences))
    if missing:
        raise LoreImportError(
            "missing-sequence", f"sequence number(s) {missing} absent from the thread"
        )
    if len(sequences) != total:
        raise LoreImportError(
            "duplicate-sequence",
            f"{len(sequences)} patch messages for a {total}-patch series",
        )

    return sorted(patches, key=lambda m: m.sequence)


# ---------------------------------------------------------------------------
# Emit
# ---------------------------------------------------------------------------


def repo_relative(path: Path) -> str:
    """Ledger paths are repo-relative so two checkouts produce the same bytes."""
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def canonical_json(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def import_series(args: argparse.Namespace) -> dict:
    fetch = fetch_thread(
        args.msgid,
        thread_file=Path(args.thread_file) if args.thread_file else None,
        allow_network=not args.no_network,
    )
    if args.expect_compressed_sha256 and fetch.compressed_sha256 != args.expect_compressed_sha256:
        raise LoreImportError(
            "digest-mismatch",
            f"thread_compressed_sha256 {fetch.compressed_sha256} != "
            f"expected {args.expect_compressed_sha256}",
        )
    if args.expect_mbox_sha256 and fetch.mbox_sha256 != args.expect_mbox_sha256:
        raise LoreImportError(
            "digest-mismatch",
            f"thread_mbox_sha256 {fetch.mbox_sha256} != expected {args.expect_mbox_sha256}",
        )

    messages = build_messages(deduplicate(split_thread(fetch.mbox)))
    patches = screen_series(messages, args.expect_revision)

    lane_dir = Path(args.lane_dir)
    canonical_dir = Path(args.canonical_dir) / args.alias
    entries: list[dict] = []
    for offset, message in enumerate(patches):
        ordinal = args.ordinal_start + offset
        slug = args.slug if len(patches) == 1 else f"{args.slug}-{message.sequence}"
        name = f"{ordinal:04d}-{slug}.patch"
        entries.append(
            {
                "canonical_mail": repo_relative(canonical_dir / f"{message.sequence:02d}.mbox"),
                "canonical_patch_sha256": message.canonical_sha256,
                "date": message.date,
                "diff_sha256": message.diff_sha256,
                "filename": name,
                "from": message.author,
                "lore_msgid": message.msgid,
                "ordinal": ordinal,
                "review_tags": list(message.review_tags),
                "sequence": message.sequence,
                "subject": message.subject,
                "total": message.total,
            }
        )

    ledger = {
        "alias": args.alias,
        "lane": lane_dir.name,
        "patches": entries,
        "posted_date": patches[0].date,
        "revision": patches[0].revision,
        "thread_compressed_sha256": fetch.compressed_sha256,
        "thread_lore_msgid": args.msgid,
        "thread_mbox_sha256": fetch.mbox_sha256,
        "thread_url": fetch.url,
        "verdict": "IMPORTED",
    }

    if not args.dry_run:
        lane_dir.mkdir(parents=True, exist_ok=True)
        canonical_dir.mkdir(parents=True, exist_ok=True)
        for message, entry in zip(patches, entries):
            (lane_dir / entry["filename"]).write_text(
                message.diff_text, encoding="utf-8", errors="surrogateescape"
            )
            (canonical_dir / f"{message.sequence:02d}.mbox").write_bytes(
                message.canonical_bytes
            )
        if args.ledger:
            Path(args.ledger).parent.mkdir(parents=True, exist_ok=True)
            Path(args.ledger).write_text(canonical_json(ledger), encoding="utf-8")
    return ledger


def out_verdict(args: argparse.Namespace, error: LoreImportError) -> dict:
    verdict = {
        "alias": args.alias,
        "diagnostics": discovery_probe(args.msgid) if not args.no_network else {},
        "disposition": "OUT",
        "error_class": error.error_class,
        "error_detail": error.detail,
        "note": (
            "Discovery endpoints are diagnostic only. They cannot populate "
            "thread_compressed_sha256 or a patch body, and nothing here was "
            "hand-transcribed."
        ),
        "thread_lore_msgid": args.msgid,
        "thread_url": thread_url(args.msgid),
        "verdict": "NOT IMPORTED",
    }
    if args.ledger:
        Path(args.ledger).parent.mkdir(parents=True, exist_ok=True)
        Path(args.ledger).write_text(canonical_json(verdict), encoding="utf-8")
    return verdict


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--msgid", required=True, help="thread-root Message-ID")
    parser.add_argument("--alias", required=True, help="matrix alias, e.g. U2")
    parser.add_argument("--slug", default="lore-import", help="filename slug")
    parser.add_argument("--expect-revision", default=None, help="e.g. v3")
    parser.add_argument("--ordinal-start", type=int, default=10)
    parser.add_argument("--lane-dir", default=str(ROOT / "backports"))
    parser.add_argument("--canonical-dir", default=str(ROOT / "backports" / "lore"))
    parser.add_argument("--ledger", default=None)
    parser.add_argument("--thread-file", default=None, help="offline t.mbox.gz bytes")
    parser.add_argument("--expect-compressed-sha256", default=None)
    parser.add_argument("--expect-mbox-sha256", default=None)
    parser.add_argument("--no-network", action="store_true")
    parser.add_argument("--probe-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.probe_only:
        print(
            canonical_json(
                out_verdict(
                    args,
                    LoreImportError(
                        "unfetchable-canonical-thread", "probe-only run, no import"
                    ),
                )
            ),
            end="",
        )
        return 1
    try:
        ledger = import_series(args)
    except LoreImportError as exc:
        print(f"REJECT {exc}", file=sys.stderr)
        print(canonical_json(out_verdict(args, exc)), end="")
        return 1
    print(canonical_json(ledger), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
