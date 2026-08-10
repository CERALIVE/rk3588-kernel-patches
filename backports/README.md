# `backports/` — externally-sourced patches

The third source lane. `upstream/` is Ross Cawston's import, `ceralive/` is
first-party work, and this is everything else: a patch lifted from mainline, a
stable tree, or a posting on lore that the pinned kernel does not carry yet.

One member today, `0007-iommu-rockchip-disable-fetch-dte-time-limit.patch`,
backported from mainline `8d4346ecd495`. The lane exists so that a backport does
not get dropped into `upstream/`, which would break the one claim this repository
cannot afford to lose — that `upstream/` is byte-identical to what was published
at `UPSTREAM_PATCHES_REV`.

## Why it cannot share the `upstream/` lane

`scripts/build-series.py` hard-codes a single credit block for `upstream/`:
*"Imported from `<UPSTREAM_PATCHES_REPO>` at `<UPSTREAM_PATCHES_REV>` … Authored by
Ross Cawston."* That is true of every file in that directory and of nothing else.
A backport from linux-media has a different author, a different tree and a
different licence trail, so it carries **its own** provenance instead of
inheriting that one.

## What a member of this lane must carry

Each `backports/` entry in `SERIES` is a `Patch(origin=BACKPORTS, …)`
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
