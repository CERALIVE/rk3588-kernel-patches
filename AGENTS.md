# rk3588-kernel-patches

## ROLE IN THE GROUP

Holds the **mainline-track RK3588 kernel patch series** for CeraLive: VEPU580
hardware encoder plus three HDMI-RX fixes, converted to a `git am` mailbox series
and pinned to an exact kernel tag.

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
├── upstream/                  # Ross Cawston's raw diff -ruN files, VERBATIM + README.MD
├── patches/                   # GENERATED git-am series + series file — NEVER hand-edit
├── overlays/                  # rockchip-rk3588-rkvenc-mpp.dts, verbatim
├── rebase/<tag>.rules         # per-kernel-tag context re-anchors (context lines ONLY)
├── scripts/
│   ├── preflight.sh           # re-resolve the Armbian edge mapping; --head for live check
│   ├── build-series.py        # upstream/ -> patches/ ; --check asserts in-sync
│   ├── verify-payload-parity.py  # proves patches/ changes nothing upstream/ didn't
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
| Check whether Armbian moved `edge` | `scripts/preflight.sh --head` |
| Understand the 7.1 derivation | [`docs/PREFLIGHT.md`](docs/PREFLIGHT.md) |
| Apply the series | `scripts/apply.sh` — see [`README.md`](README.md) |
| Why a hunk was re-anchored | [`docs/REBASE-v7.1.5.md`](docs/REBASE-v7.1.5.md) |
| Licence / redistribution facts | [`docs/PROVENANCE.md`](docs/PROVENANCE.md) |
| Why not the `sfqr0414` fork | [`README.md`](README.md) → "Why not the `sfqr0414` fork" |

## KEY FACTS

**`patches/` is generated. Editing it by hand is a bug, and CI catches it.**
`scripts/build-series.py --check` regenerates from `upstream/` into a temp dir and
byte-compares. Change `upstream/` or `rebase/<tag>.rules`, then regenerate — never
the other way round.

**Upstream's `git am` instruction has never worked — that is why this fork exists.**
The upstream files are raw `diff -ruN aa/ bb/` output with **no mail headers**, so
`git am` fails format detection before reading a hunk. `0001` and `0003` also carry
9 macOS `.DS_Store` `Binary files … differ` stanzas, which `git apply` refuses
("cannot apply binary patch … without full index line") even once headers exist.
`build-series.py` fixes both. Any instruction this repo publishes is executed
verbatim by CI, so it cannot rot the same way.

**Upstream numbering is preserved, gap included: `0001`, `0002`, `0003`, `0005`.**
There is no `0004` upstream. **Do NOT renumber to close the gap** — the 1:1 filename
correspondence with upstream is what makes the import auditable. Subject ordinals
read `1/5`, `2/5`, `3/5`, `5/5` for the same reason.

**The conflict rule is machine-enforced, not a convention.** A `rebase/*.rules`
entry may only re-anchor **context** lines. `build-series.py` raises if a rule's
anchor resolves to a `+`/`-` line or matches ambiguously, and
`verify-payload-parity.py` independently proves the ordered set of added/removed
lines in `patches/` is byte-identical to `upstream/`. If a conflict cannot be fixed
that way it is **behavioural**: STOP, write it up in `docs/REBASE-<tag>.md`, and
report the series as not applying. **Never invent a resolution** — this is
especially true for `0001`, ~4,200 lines of ported vendor driver code whose real
conflicts need someone who can test on RK3588 hardware.

**We pin a TAG; Armbian tracks a BRANCH.** Armbian's `edge` resolves to
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
derivation audit of the ported code was done. We use the GPL-2.0 branch only.
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
| `series-integrity` | `patches/` is generated and payload-identical to `upstream/`; no Python needed beyond stdlib |
| `preflight` | `kernel-pin.env` still matches `armbian/build` — non-blocking on schedule, blocking on PR |
| `apply` | `scripts/apply.sh` — the real `git am` against the pinned tag |

`apply` is the gate. It runs the same script the README tells humans to run, so a
broken instruction is a red build.

There is **no build job**, deliberately. Adding one means a cross-compiler, a
defconfig, and a 30-minute job to prove something the image pipeline proves better.

## ANTI-PATTERNS

- Don't hand-edit `patches/` — regenerate from `upstream/` + `rebase/`
- Don't renumber the series to close the `0004` gap
- Don't put a behavioural fix in `rebase/*.rules` — that is what the stop ledger is for
- Don't add a `+`/`-` line anywhere in this repo's patch pipeline; payload parity must hold
- Don't follow `linux-7.1.y` downstream — pin `KERNEL_TAG`
- Don't bump `KERNEL_TAG` without `scripts/preflight.sh --head` and a new `docs/REBASE-<tag>.md`
- Don't add this repo to `REPOS` or `versions.yaml` — it ships no artifact
- Don't let `gh pr create` pick the base branch (see PR TARGETING)
- Don't claim upstream-mergeable status, or assert the MIT branch of the licence
- Don't treat this repo's existence as reopening image-pipeline Decision D3
