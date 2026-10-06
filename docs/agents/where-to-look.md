<!-- Moved verbatim from AGENTS.md on 2026-10-05 by lean-rules-docs-landing-latam -->

## WHERE TO LOOK

| Task | Location |
|------|----------|
| Change the target kernel | [`kernel-pin.env`](https://github.com/CERALIVE/rk3588-kernel-patches/blob/main/kernel-pin.env) + a new `rebase/<tag>.rules` + a new `docs/REBASE-<tag>.md` |
| Add a CeraLive-authored patch | `ceralive/<NNNN>-*.patch` + a `SERIES` entry with `origin=CERALIVE` in `scripts/build-series.py`, then regenerate |
| Add a patch taken from a MERGED mainline commit | `backports/<NNNN>-*.patch` + a `SERIES` entry with `origin=BACKPORTS` **and** a `Backport(...)` — see [`backports/README.md`](https://github.com/CERALIVE/rk3588-kernel-patches/blob/main/backports/README.md) |
| Add a patch taken from an UNMERGED lore posting | run `scripts/import-lore-series.py`, then a `SERIES` entry with `origin=BACKPORTS`, `provenance=LORE_POSTING` **and** a `LorePosting(...)` — see [`backports/README.md`](https://github.com/CERALIVE/rk3588-kernel-patches/blob/main/backports/README.md) |
| Import an island release | Copy its mailbox members byte-preserved into `island/`, continue the ordinal counter, and use `provenance=Island(tag=…, commit=…, asset_sha256=…)`; verify with `scripts/verify-island-provenance.py` |
| Whether a screened candidate was taken, and why | [`docs/UPSTREAM-STATUS.md`](https://github.com/CERALIVE/rk3588-kernel-patches/blob/main/docs/UPSTREAM-STATUS.md) § 2026-08 candidate reconciliation matrix |
| Whether a patch has an upstream counterpart / can be dropped yet | [`docs/UPSTREAM-STATUS.md`](https://github.com/CERALIVE/rk3588-kernel-patches/blob/main/docs/UPSTREAM-STATUS.md) |
| Historical board qualification evidence and its exact base | [`docs/BOARD-QUALIFICATION.md`](https://github.com/CERALIVE/rk3588-kernel-patches/blob/main/docs/BOARD-QUALIFICATION.md) |
| Why the `system-uncached` heap exists, and why its NAME is not negotiable | [`docs/UPSTREAM-STATUS.md`](https://github.com/CERALIVE/rk3588-kernel-patches/blob/main/docs/UPSTREAM-STATUS.md) § `0009` and `patches/0009-*`'s own mail header |
| Why `0002` was kept instead of taking the upstream EDID fix | [`docs/EVAL-0002-EDID.md`](https://github.com/CERALIVE/rk3588-kernel-patches/blob/main/docs/EVAL-0002-EDID.md) |
| Why `0005`+`0006` were kept instead of taking the lore HDMI-audio series | [`docs/EVAL-0005-AUDIO.md`](https://github.com/CERALIVE/rk3588-kernel-patches/blob/main/docs/EVAL-0005-AUDIO.md) |
| Stop carrying a patch | **Never `git rm` it.** Move it to `retired/` and add a row — see [`retired/REGISTRY.md`](https://github.com/CERALIVE/rk3588-kernel-patches/blob/main/retired/REGISTRY.md) |
| How the audio v4 migration was gated, and what it does NOT prove | [`docs/AUDIO-V4-VALIDATION.md`](https://github.com/CERALIVE/rk3588-kernel-patches/blob/main/docs/AUDIO-V4-VALIDATION.md) |
| Board procedure for the `0040` EDID streaming guard | [`docs/EDID-STREAMING-GUARD.md`](https://github.com/CERALIVE/rk3588-kernel-patches/blob/main/docs/EDID-STREAMING-GUARD.md) |
| Why HDMI-RX audio needs a DT patch at all | [`docs/PROVENANCE.md`](https://github.com/CERALIVE/rk3588-kernel-patches/blob/main/docs/PROVENANCE.md) §8 and the archived `retired/0006-*`'s own mail header — the live wiring is `0044` + `0049` |
| Why the rkvenc DMA segment-size fix existed, and why the IOVA guardrail was left alone | [`docs/UPSTREAM-STATUS.md`](https://github.com/CERALIVE/rk3588-kernel-patches/blob/main/docs/UPSTREAM-STATUS.md) § `0008` and the archived `retired/0008-*`'s own mail header; the live intent is island source |
| Report the selected Armbian alias | `scripts/preflight.sh --head` |
| Understand the `bleedingedge` → 7.2 derivation | [`docs/PREFLIGHT.md`](https://github.com/CERALIVE/rk3588-kernel-patches/blob/main/docs/PREFLIGHT.md) |
| Apply the series | `scripts/apply.sh` — see [`README.md`](https://github.com/CERALIVE/rk3588-kernel-patches/blob/main/README.md) |
| Why a hunk was re-anchored, or a member revised, at the current base | [`docs/REBASE-v7.2.md`](https://github.com/CERALIVE/rk3588-kernel-patches/blob/main/docs/REBASE-v7.2.md) |
| What an earlier base needed | [`docs/REBASE-v7.1.7.md`](https://github.com/CERALIVE/rk3588-kernel-patches/blob/main/docs/REBASE-v7.1.7.md), [`docs/REBASE-v7.1.5.md`](https://github.com/CERALIVE/rk3588-kernel-patches/blob/main/docs/REBASE-v7.1.5.md) |
| Why an ordinal is retired, and where its file went | [`retired/REGISTRY.md`](https://github.com/CERALIVE/rk3588-kernel-patches/blob/main/retired/REGISTRY.md) + [`docs/UPSTREAM-STATUS.md` § retired ordinals](https://github.com/CERALIVE/rk3588-kernel-patches/blob/main/docs/UPSTREAM-STATUS.md#retired-ordinals-0007-0023-0024-0025) |
| Licence / redistribution facts | [`docs/PROVENANCE.md`](https://github.com/CERALIVE/rk3588-kernel-patches/blob/main/docs/PROVENANCE.md) |
| Why not the `sfqr0414` fork | [`README.md`](https://github.com/CERALIVE/rk3588-kernel-patches/blob/main/README.md) → "Why not the `sfqr0414` fork" |

