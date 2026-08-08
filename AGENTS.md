# rk3588-kernel-patches

## ROLE IN THE GROUP

Holds the **mainline-track RK3588 kernel patch series** for CeraLive: VEPU580
hardware encoder plus three HDMI-RX fixes imported from upstream, plus the
first-party device-tree patch that makes HDMI-RX audio actually capturable —
converted to a `git am` mailbox series and pinned to an exact kernel tag.

Produces **patch text only** — no `.deb`, no kernel, no image artifact. It is
therefore **NOT in the device image `REPOS` array** and has **no `versions.yaml`
pin**, for the same reason `ceralive-infra` has none: there is nothing for the
image pipeline to fetch.

Relates to:
- `image-building-pipeline/` — the intended downstream consumer. A future
  kernel-build-from-source stage sources `kernel-pin.env` for the exact tag. The
  **shipped** image is unaffected (see KEY FACTS).
- `cerastream/` — the encoder this series enables is the mainline-track
  alternative to the vendor MPP path cerastream uses today.

Upstream: GitHub fork of
[`rcawston/rockchip-rk3588-mainline-patches`](https://github.com/rcawston/rockchip-rk3588-mainline-patches),
imported at `e13a311` (2026-07-01).

## STRUCTURE

```
rk3588-kernel-patches/
├── kernel-pin.env             # SINGLE SOURCE OF TRUTH for every pinned coordinate
├── upstream/                  # SOURCE LANE — Ross Cawston's raw diff -ruN files, VERBATIM + README.MD
├── ceralive/                  # SOURCE LANE — FIRST-PARTY raw diffs with no upstream counterpart
├── backports/                 # SOURCE LANE — externally-sourced patches, each carrying its OWN provenance
├── retired/                   # ARCHIVE — patches moved out of the series, byte-unchanged
│   └── REGISTRY.md            # the RETIRED registry: state machine + the retirement table
├── patches/                   # GENERATED git-am series + series file — NEVER hand-edit
├── overlays/                  # rockchip-rk3588-rkvenc-mpp.dts, verbatim
├── rebase/<tag>.rules         # per-kernel-tag context re-anchors (context lines ONLY)
├── scripts/
│   ├── preflight.sh           # re-resolve the Armbian edge mapping; --head for live check
│   ├── build-series.py        # source lanes -> patches/ ; --check asserts in-sync; orphan check
│   ├── verify-payload-parity.py  # proves patches/ changes nothing its source lane didn't
│   └── apply.sh               # the gate: verify -> clone pinned tag -> git am -> assert
├── docs/
│   ├── PROVENANCE.md          # licence/provenance audit incl. the MIT-claim caveat
│   ├── PREFLIGHT.md           # how the Armbian edge -> 7.1 mapping was derived
│   └── REBASE-v7.1.5.md       # hunk-by-hunk rebase ledger
└── .github/workflows/patch-apply.yml
```

## WHERE TO LOOK

| Task | Location |
|------|----------|
| Change the target kernel | [`kernel-pin.env`](kernel-pin.env) + a new `rebase/<tag>.rules` + a new `docs/REBASE-<tag>.md` |
| Add a CeraLive-authored patch | `ceralive/<NNNN>-*.patch` + a `SERIES` entry with `origin=CERALIVE` in `scripts/build-series.py`, then regenerate |
| Add a patch taken from mainline / lore | `backports/<NNNN>-*.patch` + a `SERIES` entry with `origin=BACKPORTS` **and** a `Backport(...)` — see [`backports/README.md`](backports/README.md) |
| Stop carrying a patch | **Never `git rm` it.** Move it to `retired/` and add a row — see [`retired/REGISTRY.md`](retired/REGISTRY.md) |
| Why HDMI-RX audio needs a DT patch at all | [`docs/PROVENANCE.md`](docs/PROVENANCE.md) §8 and `patches/0006-*`'s own mail header |
| Check whether Armbian moved `edge` | `scripts/preflight.sh --head` |
| Understand the 7.1 derivation | [`docs/PREFLIGHT.md`](docs/PREFLIGHT.md) |
| Apply the series | `scripts/apply.sh` — see [`README.md`](README.md) |
| Why a hunk was re-anchored | [`docs/REBASE-v7.1.5.md`](docs/REBASE-v7.1.5.md) |
| Licence / redistribution facts | [`docs/PROVENANCE.md`](docs/PROVENANCE.md) |
| Why not the `sfqr0414` fork | [`README.md`](README.md) → "Why not the `sfqr0414` fork" |

## KEY FACTS

**`patches/` is generated. Editing it by hand is a bug, and CI catches it.**
`scripts/build-series.py --check` regenerates from `upstream/` + `ceralive/` into a
temp dir and byte-compares. Change a source lane or `rebase/<tag>.rules`, then
regenerate — never the other way round.

**Three source lanes, one pipeline: `upstream/` is imported, `ceralive/` is ours,
`backports/` is everyone else's.** `upstream/` must stay byte-identical to Ross
Cawston's published files forever — that is what makes the credit line, the licence
audit and the parity claim checkable. A patch CeraLive authors goes in `ceralive/`
and continues the same numbering (`0006` and up). A patch lifted from mainline, a
stable tree or a lore posting goes in `backports/`. All three lanes run through
`build-series.py`, get the same context-only rebase discipline, and are held to the
same added/removed-line parity by `verify-payload-parity.py` — the lane only changes
which mail header is written and which directory parity is proven against. **Never
put first-party or backported content in `upstream/`.**

**`backports/` carries provenance per patch, because it cannot inherit one.** The
`upstream/` lane hard-codes a single credit block — *"Imported from
`UPSTREAM_PATCHES_REPO` at `UPSTREAM_PATCHES_REV` … Authored by Ross Cawston"* —
which is true of every file in that directory and of nothing else. So every
`backports/` member must name its own origin: `provenance` is the 40-hex commit it
is backported from (never `NULL_OID`, which is 40 hex digits and would otherwise
pass the shape test), and a `Backport(upstream_subject=…, lore_msgid=…, note=…)`
supplies the rest. The generated header emits the stable-tree
`commit <sha> upstream.` marker plus a `https://lore.kernel.org/r/<msgid>` link.
The build refuses a `backports/` entry that lacks any of it.
Details: [`backports/README.md`](backports/README.md).

**Retirement, not deletion — `retired/` + a registry row is the ONLY way out.**
Deleting a source file would make "`upstream/` is byte-identical to what was
imported" unfalsifiable: a reviewer cannot tell "upstream published four" from
"someone quietly dropped the fifth". So a patch that stops being carried is **moved
byte-unchanged** into `retired/` and gains a row in
[`retired/REGISTRY.md`](retired/REGISTRY.md) — a Markdown table that is the doc and
the machine input at once, the same choice `rebase/*.rules` makes, so there is no
second copy to drift. Reinstating is the reverse: move back, restore the entry with
its **original** ordinal, drop the row. Retired ordinals are never reused, exactly
as the `0004` gap is never closed.

**Membership is exactly-once, both directions, and the build enforces it.**
`build-series.py` used to walk a hard-coded `SERIES` table and never look at the
directories, so a new file dropped into `upstream/` or `backports/` was a silent
no-op. Now every `*.patch` under a source lane must be **either** an active `SERIES`
member **or** a registered retirement — never both, never neither. A registry row
with no archived file, an archived file with no row, a file present in two lanes,
a duplicate `SERIES` entry, and a reused ordinal all fail the build.
`verify-payload-parity.py` re-derives the same orphan check from the filesystem
alone, so the two opinions stay independent.

**Upstream's `git am` instruction has never worked — that is why this fork exists.**
The upstream files are raw `diff -ruN aa/ bb/` output with **no mail headers**, so
`git am` fails format detection before reading a hunk. `0001` and `0003` also carry
9 macOS `.DS_Store` `Binary files … differ` stanzas, which `git apply` refuses
("cannot apply binary patch … without full index line") even once headers exist.
`build-series.py` fixes both. Any instruction this repo publishes is executed
verbatim by CI, so it cannot rot the same way.

**Upstream numbering is preserved, gap included: `0001`, `0002`, `0003`, `0005`.**
There is no `0004` upstream. **Do NOT renumber to close the gap** — the 1:1 filename
correspondence with upstream is what makes the import auditable. First-party patches
continue the same counter (`0006` …), so the ordinals read `1/6`, `2/6`, `3/6`,
`5/6`, `6/6` — the gap at 4 stays visible, which is the whole point.

**`0005` is driver-only; `0006` is what makes HDMI-RX audio reachable.** Upstream's
`0005` registers an ASoC `hdmi-audio-codec` child under `hdmi_receiver@fdee0000`
and drives the receiver's audio FIFO/ACR/clock, but touches no device tree, and
ALSA does not create a card for a bare codec. On a Rock 5B+ running only `0001`–
`0005` the codec device is *bound* with no cable attached while `/proc/asound/cards`
shows no HDMI-RX capture card at all. `0006` supplies the three missing DT facts:
`#sound-dai-cells` on `hdmi_receiver`, an `hdmirx-sound` `simple-audio-card`, and
`&i2s7_8ch` + `&hdmirx_sound` enabled on the two CeraLive boards. `apply.sh` asserts
all of them post-apply, per board, because the failure mode is silent — everything
probes, nothing errors, there is simply no capture device.

**The `78c67d98f221` HDMI-codec regression does NOT apply to this tree.** An
`armbian/linux-rockchip` commit zeroes `capture.channels_min/max` for every
`hdmi-audio-codec` instance with no TX/RX discrimination, which breaks HDMI-RX
capture on the **vendor** BSP (`rk-6.1-rkr6.1`). Mainline — including the pinned
`v7.1.5` — already carries the upstream `no_i2s_playback` / `no_i2s_capture` /
`no_spdif_*` pdata flags and only clears a direction when the registering driver
asks. There is nothing to fix here, and a backport of that vendor-side fix would
not even apply. Do not add one — the vendor-side fix lives in its own sibling
repo, [`CERALIVE/rk3588-vendor-kernel-patches`](https://github.com/CERALIVE/rk3588-vendor-kernel-patches),
pinned to `rk-6.1-rkr5.1` (the vendor branch the shipped image actually runs).
Send anyone who lands here looking for it there, and do not duplicate it here.

**The conflict rule is machine-enforced, not a convention.** A `rebase/*.rules`
entry may only re-anchor **context** lines. `build-series.py` raises if a rule's
anchor resolves to a `+`/`-` line or matches ambiguously, and
`verify-payload-parity.py` independently proves the ordered set of added/removed
lines in `patches/` is byte-identical to `upstream/`. If a conflict cannot be fixed
that way it is **behavioural**: STOP, write it up in `docs/REBASE-<tag>.md`, and
report the series as not applying. **Never invent a resolution** — this is
especially true for `0001`, ~4,200 lines of ported vendor driver code whose real
conflicts need someone who can test on RK3588 hardware.

**This repo pins a TAG; Armbian tracks a BRANCH.** Armbian's `edge` resolves to
`KERNELBRANCH="branch:linux-7.1.y"`, a rolling stable branch. This repo pins
`v7.1.5` = `155b42bec9cbb6b8cdc47dd9bd09503a81fbe493`, the tip of that branch at
import. `apply.sh` refuses to run if the tag in the tree does not resolve to the
pinned commit, so a moved tag fails loudly instead of going green against the wrong
source. **Downstream consumers must pin the same tag**, not follow `linux-7.1.y`.

**The `edge` mapping was verified fresh, and the family config is a trap.**
`config/sources/families/rockchip-rk3588.conf` handles only `legacy` and `vendor`
in its own `case $BRANCH` — reading it alone suggests `edge` is unsupported. In
fact it sources `rockchip64_common.inc` on line 10, and *that* file's `edge)` arm
sets `KERNEL_MAJOR_MINOR=7.1`. `preflight.sh` asserts the absence of an `edge)` case
in the family config precisely so a future Armbian change there cannot silently
invalidate the derivation.

**This does NOT change the shipped image's kernel.** The shipped image is locked to
the Armbian **vendor** BSP (`rk-6.1-rkr5.1`, `linux-image-vendor-rk35xx`) — image
pipeline Decision D3. That BSP has its own in-tree rkvenc/MPP stack and does not
need this series. This repo is the mainline-track option, kept applying and
audited; it is not a pending migration. Do not read its existence as reopening D3.

**Scope is patch application only.** No kernel is built, nothing is compiled, no
hardware is touched, and the DT overlay is carried verbatim without being compiled.
Kernel builds belong to `image-building-pipeline`.

**No MIT claim is made anywhere.** The new sources carry
`(GPL-2.0+ OR MIT)` + `MODULE_LICENSE("Dual MIT/GPL")`, and the Rockchip BSP
originals were verified to carry the same tags — so the dual grant is inherited,
not invented. But the upstream repo has **no `LICENSE` file**, and no line-by-line
derivation audit of the ported code was done. Only the GPL-2.0 branch is used.
Details and open questions: [`docs/PROVENANCE.md`](docs/PROVENANCE.md).

## PR TARGETING — READ THIS FIRST

**This repository is a GitHub fork, so `gh pr create` defaults its base to
`rcawston/rockchip-rk3588-mainline-patches`.** That is the exact failure mode the
root `AGENTS.md` records as having already sent a `srtla-send-rs` PR to
`irlserver/srtla_send`. Always be explicit:

```bash
gh pr create --repo CERALIVE/rk3588-kernel-patches --base main
gh pr view <n> --json url -q .url   # MUST be https://github.com/CERALIVE/...
```

Keep **only** `origin` (CERALIVE) attached at rest. If an upstream-sync ever needs
the parent, add it transiently as `rcawston` (**never** as `upstream`), fetch with
an explicit refspec, pin-verify the SHA, and remove it before any push or PR.

An upstream-sync PR that carries a real `git merge` commit must be **merge-commit
merged, never squashed** — squashing discards the second parent, so `git merge-base`
never advances and every later sync replays as phantom conflicts.

## CI

One workflow, `patch-apply.yml`, following the root CI/CD canon: `concurrency` with
`cancel-in-progress: true`; `push` constrained to `branches:` because a
`pull_request` trigger exists; top-level `permissions: contents: read`; actions
pinned to latest stable major; the ~2 GB kernel clone cached. Jobs:

| Job | Asserts |
|-----|---------|
| `series-integrity` | `patches/` is generated, payload-identical to its source lane (`upstream/`, `ceralive/` or `backports/`), and every lane file is accounted for exactly once; no Python needed beyond stdlib |
| `pin` | nothing — it *reads* `KERNEL_TAG` out of `kernel-pin.env` and emits the `apply` matrix |
| `preflight` | `kernel-pin.env` still matches `armbian/build` — non-blocking on schedule, blocking on PR |
| `apply` | `scripts/apply.sh` — the real `git am` against the pinned tag |

`apply` is the gate. It runs the same script the README tells humans to run, so a
broken instruction is a red build.

**No workflow restates a pinned coordinate.** The `apply` matrix used to be
`tag: [v7.1.5]`, which meant a `KERNEL_TAG` bump left CI proving the series against
a kernel nobody ships — and doing it *green*, which is the worst kind of failure.
The `pin` job now reads the tag from `kernel-pin.env` and the matrix is
`fromJSON(needs.pin.outputs.tags)`. There is no literal kernel tag anywhere in
`.github/`, and adding one back is a regression. `apply` still cross-checks its
matrix entry against `KERNEL_TAG`, because the cached commit it verifies against is
`KERNEL_COMMIT` and that is the commit of `KERNEL_TAG` and of nothing else.

There is **no build job**, deliberately. Adding one means a cross-compiler, a
defconfig, and a 30-minute job to prove something the image pipeline proves better.

## ANTI-PATTERNS

- Don't hand-edit `patches/` — regenerate from `upstream/` / `ceralive/` / `backports/` + `rebase/`
- Don't put CeraLive-authored or backported content in `upstream/`, or upstream content in the other lanes
- Don't make `verify-payload-parity.py` import from `build-series.py` — it is
  deliberately the second, independent opinion
- Don't `git rm` a source-lane patch — move it to `retired/` and register it
- Don't add a `backports/` patch without its own commit sha and lore Message-ID
- Don't renumber the series to close the `0004` gap, or reuse a retired ordinal
- Don't restate a pinned coordinate in a workflow — read it from `kernel-pin.env`
- Don't strip quotes off a `kernel-pin.env` value by hand; `read_pin()` parses it
  the way bash does, inline `#` comments included
- Don't put a behavioural fix in `rebase/*.rules` — that is what the stop ledger is for
- Don't add a `+`/`-` line anywhere in this repo's patch pipeline; payload parity must hold
- Don't follow `linux-7.1.y` downstream — pin `KERNEL_TAG`
- Don't bump `KERNEL_TAG` without `scripts/preflight.sh --head` and a new `docs/REBASE-<tag>.md`
- Don't add this repo to `REPOS` or `versions.yaml` — it ships no artifact
- Don't let `gh pr create` pick the base branch (see PR TARGETING)
- Don't claim upstream-mergeable status, or assert the MIT branch of the licence
- Don't treat this repo's existence as reopening image-pipeline Decision D3
