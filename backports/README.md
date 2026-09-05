# `backports/` — externally-sourced patches

The third source lane. `upstream/` is Ross Cawston's import, `ceralive/` is
first-party work, and this is everything else: a patch lifted from mainline, a
stable tree, or a posting on lore that the pinned kernel does not carry yet.

Seven active members today: `0010`, `0011`, `0012`, and the four HDMI-RX audio
v4 members `0042`–`0045`, all **unmerged lore postings**. `0007` is archived in
`retired/` because the base absorbed its mainline commit. The lane exists so that a backport does not get
dropped into `upstream/`, which would break the one claim this repository cannot
afford to lose — that `upstream/` is byte-identical to what was published at
`UPSTREAM_PATCHES_REV`.

## Two provenance variants, and they are not interchangeable

A merged commit and an unmerged posting are different kinds of thing, and the
generated header has to say which one it is looking at. `build-series.py` refuses
an entry that carries both, or neither.

| Variant | Field | The header says | Retires when |
|---|---|---|---|
| merged commit | `Backport(...)` + a 40-hex `provenance` | `commit <sha> upstream.` | the base absorbs that commit |
| unmerged posting | `LorePosting(...)` + `provenance=LORE_POSTING` | `Backport of unmerged <vN> posting.` | the posting merges **and** the base absorbs it |

**An unmerged posting never receives a commit id, and that is a correctness rule,
not a style one.** `NULL_OID` is forty hex digits and would sail through every
shape test while asserting the patch came from the null commit; a parent SHA
asserts a merge that did not happen; the stable-tree `commit <sha> upstream.`
marker asserts both at once. There is no identity to state, so the header states
its absence instead. `scripts/check-series-ledger.py` fails the build if a
lore-provenance header ever grows one.

### What a `LorePosting` must carry

| Field | What it is |
|-------|-----------|
| `lore_msgid` | Message-ID of the posting, no angle brackets |
| `revision` | `vN` as posted — `v1` for a bare `[PATCH]` |
| `posted_date` | the posting's own `Date:` |
| `upstream_subject` | the posting's subject as sent |
| `thread_compressed_sha256` | sha256 of the `t.mbox.gz` **response bytes, exactly as served** |
| `thread_mbox_sha256` | sha256 of the **mailbox those bytes decompress to** — a different domain, never the same value |
| `canonical_patch_sha256` | sha256 of this one posting's canonical mail |
| `canonical_mail` | in-tree path to that canonical mail, under `backports/lore/<alias>/` |
| `review_state` | who reviewed it, what they asked for, and whether it was answered |
| `note` | why this series carries it, and what the screening found |

`canonical_mail` is why the digest is worth anything: the mail is archived in the
tree, so `canonical_patch_sha256` is recomputable by anyone, offline, forever. The
two thread digests are attestations of the exact archive response the import
consumed — lore regenerates its gzip, so they are a record of a fetch rather than
a reproducible build input, and they are labelled that way in the header.

## Importing an unmerged posting

Only through `scripts/import-lore-series.py`. Never by hand — see the rule below.

```bash
scripts/import-lore-series.py \
  --msgid 1774423383-36599-1-git-send-email-shawn.lin@rock-chips.com \
  --alias U3 --expect-revision v1 --ordinal-start 10 \
  --slug phy-rockchip-naneng-combphy-force-rterm-det-rdy \
  --ledger .omo/evidence/<effort>/import-U3.json
```

The importer requires a successful `all/<msgid>/t.mbox.gz` fetch. `patchwork` and
`/r/<msgid>/raw` are **discovery instruments only**: they can tell you a
Message-ID resolves somewhere, which is enough to justify an OUT
`unfetchable-canonical-thread` verdict, and they may never supply a patch body or
a thread digest. It then hashes the compressed response, decompresses under a hard
size and message-count ceiling, deduplicates by normalised Message-ID, drops cover
letters, un-escapes mboxrd `>From`, requires one coherent revision with a complete
`1..N` sequence, and writes the diff body plus the canonical mail.

Three refusals are worth knowing before you run it:

- **One Message-ID, two different canonical bodies** → reject. That is corruption,
  not a resend, and there is no defensible survivor.
- **One diff, two different Message-IDs** → reject, `duplicate-diff-distinct-msgid`.
  The candidate goes OUT `malformed-thread`. Picking a survivor here would be
  picking which posting the series claims to carry.
- **Canonical archive unreachable** → OUT `unfetchable-canonical-thread`. Do not
  transcribe the patch by hand. A hand-typed body has no digest domain at all,
  which is the entire thing this lane exists to provide.

**Lore's `/all/` view merges each posting's per-list copies**, so the same message
arrives several times with different transport headers, a different
`Content-Transfer-Encoding`, a different mailman footer, and sometimes a different
`From:` (b4's relay rewrites it to `devnull+…@kernel.org` on some copies). The
importer's canonical form is therefore `Message-ID` + `Subject` + `Date` + the
decoded body, with list footers stripped and the observed senders recorded beside
the digest rather than inside it. Raw-byte comparison would report corruption on
almost every real thread.

## Why it cannot share the `upstream/` lane

`scripts/build-series.py` hard-codes a single credit block for `upstream/`:
*"Imported from `<UPSTREAM_PATCHES_REPO>` at `<UPSTREAM_PATCHES_REV>` … Authored by
Ross Cawston."* That is true of every file in that directory and of nothing else.
A backport from linux-media has a different author, a different tree and a
different licence trail, so it carries **its own** provenance instead of
inheriting that one.

## What a merged-commit member must carry

Each merged-commit `backports/` entry in `SERIES` is a `Patch(origin=BACKPORTS, …)`
with a `Backport(...)` attached, and the build refuses the lane without one:

| Field | What it is |
|-------|-----------|
| `provenance` | The 40-hex commit being backported. It becomes the mbox delimiter, and the generated header's `commit <sha> upstream.` line — the same marker a stable-tree backport carries |
| `Backport.upstream_subject` | That commit's own subject line |
| `Backport.lore_msgid` | Message-ID of the list posting, no angle brackets; rendered as `https://lore.kernel.org/r/<msgid>` |
| `Backport.note` | Why this series carries it: what breaks without it, and why the pinned kernel lacks it |

## Everything else is identical to the other lanes

The file here is the source of record and `patches/` is generated from it — never
the other way round. `scripts/verify-payload-parity.py` holds it to byte-identical
added/removed lines, `rebase/<tag>.rules` may re-anchor its **context** only, the
orphan check fails the build if it is not in `SERIES` exactly once, and it can
only leave via [`../retired/REGISTRY.md`](../retired/REGISTRY.md).

## Before adding one

Check it is a backport and not a rebase problem. A patch that stops applying is a
conflict — that is `docs/REBASE-<tag>.md`'s job. This lane is for functionality the
pinned kernel genuinely does not have.

Also check it belongs to *this* tree. The vendor 6.1 BSP fixes live in
[`CERALIVE/rk3588-vendor-kernel-patches`](https://github.com/CERALIVE/rk3588-vendor-kernel-patches)
and do not apply here; see `AGENTS.md` on the `78c67d98f221` HDMI-codec regression.

Then check two things `git apply --check` cannot tell you, both of which have
already turned a candidate away once:

- **How deep the prerequisite chain is — as a *build*, not as a text apply.** A
  commit that references a symbol added by an earlier commit in its own series
  applies cleanly and then fails to compile. Grep the base for every identifier
  the patch introduces or calls. **More than two prerequisites and the answer is
  "not cleanly backportable"** — record it and move on rather than quietly
  importing a chain.
- **Whether the merged version has a known bug with no landed fix.** Read the
  whole thread, replies included, not just the patch. Sweep mainline for
  follow-ups per touched file
  (`api.github.com/repos/torvalds/linux/commits?path=<file>&since=<date>`); lore's
  search endpoint is 403 to `curl`, so only a thread fetched by Message-ID is
  readable. The I2S MCLK gate series was declined on both counts at once —
  [`docs/UPSTREAM-STATUS.md` § MCLK](../docs/UPSTREAM-STATUS.md#i2s-mclk-gate-clocks--skipped-known-regression-on-rock-5b).

Both checks were exercised again in the 2026-08 screening round, and both turned
candidates away: U7 (PCIe root-port reset, `PATCHv6`) fails 2/4 onward against
`v7.1.7` because it was written for a mid-2025 tree, and M2 repairs a regression
introduced by a commit the base does not carry. Every candidate, IN or OUT, has a
row in the reconciliation matrix in
[`docs/UPSTREAM-STATUS.md`](../docs/UPSTREAM-STATUS.md#2026-08-candidate-reconciliation-matrix-m1m8--u1u7);
`scripts/validate-candidate-matrix.py` refuses that block if any row or field is
missing.

For an **unmerged** posting there is a third check, and it is the one that turned
away the only T13 candidate that passed everything else — and, in the 2026-08
round, U4 as well:

- **Whether the payload is a userspace-visible interface still under
  negotiation.** A backport of merged code retires cleanly when the base absorbs
  it. A backport of a *posting* only retires cleanly if what lands is what you
  shipped — so if the thread shows the names, keys or ioctl numbers are still
  being argued about, importing means committing to an ABI upstream has already
  decided against, and the retire trigger silently stops working. The V4L2 fdinfo
  series applies to `v7.1.7` with no fuzz at exactly two prerequisites, and was
  declined because all five of its `/proc/<pid>/fdinfo` keys had already been
  agreed to be renamed in-thread —
  [`docs/UPSTREAM-STATUS.md` § fdinfo](../docs/UPSTREAM-STATUS.md#v4l2-hw-usage-stats-fdinfo--skipped-the-key-names-are-already-agreed-to-change).
  The counter-check is just as important: read the *review tags per patch*, not
  per series. The SCDC series carries five of them and **none** is on the patch
  that would have been the payload. U4 is the same trap wearing a better
  disguise: eight of its ten patches carry `Reviewed-by` from the maintainer, and
  the other two carry an unanswered request to change their behaviour — so a v5
  import would ship exactly the two patches upstream has already declined.
