# `backports/` — externally-sourced patches

The third source lane. `upstream/` is Ross Cawston's import, `ceralive/` is
first-party work, and this is everything else: a patch lifted from mainline, a
stable tree, or a posting on lore that the pinned kernel does not carry yet.

Empty today. The lane exists so that the first backport does not get dropped into
`upstream/`, which would break the one claim this repository cannot afford to
lose — that `upstream/` is byte-identical to what was published at
`UPSTREAM_PATCHES_REV`.

## Why it cannot share the `upstream/` lane

`scripts/build-series.py` hard-codes a single credit block for `upstream/`:
*"Imported from `<UPSTREAM_PATCHES_REPO>` at `<UPSTREAM_PATCHES_REV>` … Authored by
Ross Cawston."* That is true of every file in that directory and of nothing else.
A backport from linux-media has a different author, a different tree and a
different licence trail, so it carries **its own** provenance instead of
inheriting that one.

## What a member of this lane must carry

Each `backports/` entry in `SERIES` is a `Patch(origin=BACKPORTS, …)` with a
`Backport(...)` attached, and the build refuses the lane without one:

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
