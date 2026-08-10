# rk3588-kernel-patches

Out-of-tree mainline Linux patches for the Rockchip RK3588, packaged as a
**`git am`-able mailbox series** pinned to an exact kernel tag.

CeraLive fork of [`rcawston/rockchip-rk3588-mainline-patches`](https://github.com/rcawston/rockchip-rk3588-mainline-patches),
imported at `e13a311` (2026-07-01) with full history and authorship preserved.

| | |
|---|---|
| **Target kernel** | `v7.1.7` (`c7ba9d6de43e9d9bd755b1f3c19501a38898c6b6`) |
| **Why that kernel** | Armbian rk3588 `edge` → `KERNEL_MAJOR_MINOR=7.1` — derived in [`docs/PREFLIGHT.md`](docs/PREFLIGHT.md) |
| **Boards** | Radxa Rock 5B+, Orange Pi 5+ (both `BOARDFAMILY=rockchip-rk3588`) |
| **Status** | Applies cleanly. **Not run on hardware, not upstream-bound.** This repo builds nothing — the series has been compiled into a real `linux-image-7.1.7-ceralive-rk3588` `.deb` downstream by `image-building-pipeline`, which is a compile proof and *not* a hardware one. |

## What's in the series

Upstream's numbering is preserved verbatim, gap included. First-party and
backported patches continue the same counter from `0006`:

| | Patch | Source | What it does |
|---|---|---|---|
| `0001` | vepu580 encoder (v3) | `upstream/` | VEPU580 / RKVENC v2 H.265 · H.264 · JPEG hardware encoder, ported from the Rockchip BSP MPP driver. ~4,200 lines, 9 new files. |
| `0002` | hdmirx EDID fix (v1) | `upstream/` | Makes a written EDID actually visible to the HDMI source. |
| `0003` | hdmirx plugout fix (v1) | `upstream/` | Fixes a buffer overflow on repeated HDMI-RX replug. |
| *0004* | — | — | **Never published upstream.** The gap is intentional; do not renumber to close it. |
| `0005` | hdmirx audio | `upstream/` | The driver half of HDMI-RX audio capture: registers an ASoC `hdmi-audio-codec` under `hdmi_receiver@fdee0000` and drives the receiver's audio FIFO, ACR-derived sample rate and recovered clock. Adds no device tree. |
| `0006` | hdmirx audio sound card | `ceralive/` | The device-tree half. Without it `0005`'s codec is bound but ALSA never instantiates a card, so HDMI-IN audio cannot be captured at all. |
| `0007` | iommu dte-limit fix | `backports/` | Backport of mainline `8d4346ecd495`. Sets `BIT(31)` of the IOMMU's `MMU_AUTO_GATING`, without which a DTE fetch racing a page-table update blocks the IOMMU — a black screen on the VOP, and sporadic RGA3 hangs. Merged for 7.2-rc1, absent from `v7.1.7`. |
| `0008` | rkvenc DMA max segment size | `ceralive/` | **`UNVALIDATED` on hardware.** Sets the encoder's DMA max segment size in `rkvenc_hw_probe()`, so an imported dma-buf's recorded length stops being truncated to the `SZ_64K` default. Fixes a bookkeeping defect in `0001`; the IOVA guardrail that catches the symptom is deliberately left alone. |
| `0009` | `system-uncached` dma-heap | `ceralive/` | **`UNVALIDATED` on hardware.** Registers a second dma-heap named exactly `system-uncached` — the name Rockchip's MPP userspace hard-codes and mainline does not provide — with non-cacheable mappings, a one-time cache clean at allocation, and the CPU-sync steps skipped only for that heap. Without it `mpph264enc` does not register at all, and cached memory under an uncached name encodes non-deterministically. |
| `0010` | naneng-combphy RTERM erratum | `backports/` | **Unmerged lore posting** (`PATCHv1`, Shawn Lin). Forces RX-termination detect ready in `PHYREG26` so a PCIe peer's termination is seen at critical temperatures. No commit id exists and none is claimed. |
| `0011` | dw-hdmi-qp N/CTS helper | `backports/` | **Unmerged lore posting** (standalone `PATCHv3`, Simon Wright, `Reviewed-by`+`Tested-by`). Drops dw-hdmi-qp's private audio N/CTS table, which disagrees with the shared helper at several TMDS rates, for `drm_hdmi_acr_get_n_cts()`. |
| `0012` | dw-hdmi-qp audio `-EOPNOTSUPP` | `backports/` | **Unmerged lore posting** (`PATCHv1`, Detlev Casanova, two independent `Tested-by`). Stops the audio hooks returning `-ENODEV` with no mode set, which ASoC logs as a fault — hundreds of lines on an idle board, in the same dmesg buffer `0005`/`0006` are diagnosed from. |

Plus [`overlays/rockchip-rk3588-rkvenc-mpp.dts`](overlays/rockchip-rk3588-rkvenc-mpp.dts),
the device-tree overlay the encoder needs, carried verbatim.

Which of these have an upstream counterpart, how far along it is, and what would
have to be true before a patch can be dropped, is tracked per patch in
[`docs/UPSTREAM-STATUS.md`](docs/UPSTREAM-STATUS.md).

Where an upstream counterpart was evaluated as a replacement and the answer was
written down, the verdict gets its own document. So far:

- [`docs/EVAL-0002-EDID.md`](docs/EVAL-0002-EDID.md) — keeps `0002`, and explains
  why the 7.2-rc1 EDID fix is not a substitute for it (it is already in the base,
  and it fixes something else).
- [`docs/EVAL-0005-AUDIO.md`](docs/EVAL-0005-AUDIO.md) — keeps `0005`+`0006`
  against a fully-reviewed lore HDMI-audio series that *does* apply cleanly. It is
  declined because it drops multichannel handling, jack reporting and cable-pull
  teardown, and because its device-tree half enables the sound card on Orange Pi 5
  Plus only, which would silently leave Rock 5B+ with no capture card.

Two members carry an **`UNVALIDATED`** marker (`0008` and `0009`). What a real
board has to demonstrate before that marker can come off — every leg, every
command, on both boards — is
[`docs/BOARD-QUALIFICATION.md`](docs/BOARD-QUALIFICATION.md). Every item there is
deliberately unchecked: the checklist has been written, and it has not been run.

## Layout

```
upstream/          Ross Cawston's original diff -ruN files, byte-for-byte
ceralive/          first-party patches with no upstream counterpart
backports/         patches taken from mainline / a stable tree / lore
backports/lore/    canonical mail of each unmerged posting, one directory per candidate
tests/             stdlib unittest fixtures for the Python tooling
retired/           patches moved out of the series, byte-unchanged, + REGISTRY.md
patches/           the git-am series — GENERATED from the lanes, never hand-edit
overlays/          the rkvenc/MPP device-tree overlay
rebase/            per-kernel-tag context re-anchor rules
scripts/           preflight · build-series · verify-payload-parity · apply
kernel-pin.env     every pinned coordinate, in one sourceable file
docs/              provenance audit · rebase ledger · preflight derivation · upstream status · adopt-or-keep verdicts
```

All three source lanes run through the same converter, so `patches/` stays 100 %
generated and `verify-payload-parity.py` holds every patch — first-party and
backported included — to byte-identical added/removed lines against its own source
file. The build also refuses to run if any lane file is not accounted for exactly
once, so a patch dropped into a lane and forgotten is an error rather than a silent
no-op.

**A source file is never deleted.** Dropping a patch from the series moves it into
[`retired/`](retired/REGISTRY.md) byte-unchanged and records a row in the registry
there. That is what keeps "`upstream/` is exactly what was imported" checkable even
after the series stops carrying one of those files. The *precondition* for dropping
a given patch — "upstream merged it, so drop when the base reaches vX.Y" — is
recorded per patch in [`docs/UPSTREAM-STATUS.md`](docs/UPSTREAM-STATUS.md).

---

## Apply the series

Everything below is executed verbatim by CI on every push and pull request, so it
cannot silently rot.

### The short way

```bash
git clone https://github.com/CERALIVE/rk3588-kernel-patches
cd rk3588-kernel-patches
scripts/apply.sh
```

That clones the pinned kernel tag into `.work/linux`, verifies the series is
generated and payload-identical to its sources, applies it with `git am`, runs
post-apply checks, and cleans up. Roughly 2 GB of clone; use `KEEP_TREE=1` to keep
the tree, or pass your own:

```bash
KEEP_TREE=1 scripts/apply.sh                 # keep .work/linux
scripts/apply.sh /path/to/your/linux         # use an existing tree
```

`apply.sh` refuses to touch a tree with uncommitted changes, and refuses to apply
if the tag does not resolve to the pinned commit.

### The manual way

```bash
source kernel-pin.env

git clone --depth 1 -b "$KERNEL_TAG" --single-branch "$KERNEL_MIRROR" linux
cd linux

# git am needs an identity
git config user.name  "Your Name"
git config user.email "you@example.com"

git am --keep-non-patch ../patches/*.patch
```

Shell glob order is lexical, which is the correct apply order.
[`patches/series`](patches/series) records it explicitly if you need it.

### Then: kernel config

The encoder driver is not enabled by default.

```bash
./scripts/config --module CONFIG_VIDEO_ROCKCHIP_RKVENC
```

### Then: device tree

The encoder nodes are added to `rk3588-base.dtsi` by `0001`, so a stock build
picks them up. If you are instead applying the overlay at runtime on Armbian:

```bash
armbian-add-overlay overlays/rockchip-rk3588-rkvenc-mpp.dts
```

### Then: userspace

The encoder is driven through Rockchip's MPP library, not V4L2 stateful encode.
Upstream's `README.MD` (kept at [`upstream/README.MD`](upstream/README.MD))
documents building `tsukumijima/mpp-rockchip`. **Untested here** — this repository
gates patch application only.

---

## Use with `armbian-build`

Armbian applies user patches from `userpatches/`, in lexical order, per kernel
family. For `edge` on rk3588 the family directory is `rockchip64-7.1`:

```bash
git clone --depth 1 https://github.com/armbian/build
mkdir -p build/userpatches/kernel/archive/rockchip64-7.1/
cp patches/*.patch build/userpatches/kernel/archive/rockchip64-7.1/
cd build && ./compile.sh BOARD=rock-5b-plus BRANCH=edge
```

Do not copy `patches/series` into that directory — Armbian would try to apply it
as a patch.

> The family directory is derived, not guessed. It comes from
> `KERNEL_MAJOR_MINOR=7.1` + `LINUXFAMILY=rockchip64`; see
> [`docs/PREFLIGHT.md`](docs/PREFLIGHT.md). Upstream's README says
> `rockchip64-6.19`, which was right for the kernel *they* targeted.

---

## Changing the kernel pin

`kernel-pin.env` is the single source of truth. Bumping it is a deliberate act:

```bash
scripts/preflight.sh --head     # has Armbian moved edge?
# edit KERNEL_TAG / KERNEL_TAG_OBJECT / KERNEL_COMMIT together
cp rebase/v7.1.7.rules rebase/<new-tag>.rules   # seed, then re-decide every rule
scripts/apply.sh                # resolve conflicts per the rule below
```

**The rule for conflicts.** A conflict may be resolved with a `rebase/*.rules`
entry **only** if the fix changes how a patch *applies*, never what it *does*.
Anything else gets written up in a new `docs/REBASE-<tag>.md` and the series is
reported as not applying. That boundary is machine-enforced, not a convention —
see [`docs/REBASE-v7.1.7.md`](docs/REBASE-v7.1.7.md).

---

## Differences from upstream

**The upstream `git am` instruction does not work.** Upstream's `README.MD` says
`git am /path/to/patches/*.patch`, but its patch files are raw `diff -ruN` output
with no mail headers at all, so `git am` rejects them before it reads a single
hunk. Two of them additionally carry macOS `.DS_Store` `Binary files … differ`
stanzas, which `git apply` refuses even once headers exist. Fixing that is the
main reason this fork exists — `patches/` is generated from `upstream/` and
`ceralive/` by `scripts/build-series.py`, which adds mailbox headers and drops the
`.DS_Store` noise.

**The series is re-anchored for `v7.1.7`.** Upstream targeted `v6.19-rc8`. Two
context anchors drifted in between; both were re-anchored, and the five members
that existed at the re-anchor are documented hunk by hunk in
[`docs/REBASE-v7.1.7.md`](docs/REBASE-v7.1.7.md). `0007` was backported straight
onto `v7.1.7` and `0008` and `0009` were authored against it, so none of the three
needed re-anchoring and none has a ledger entry there. The earlier
[`docs/REBASE-v7.1.5.md`](docs/REBASE-v7.1.5.md) is kept as the record of the
previous base.

**Nothing the patches do was changed.** `scripts/verify-payload-parity.py` proves
that the set of added and removed lines in `patches/` is byte-identical to the
patch's source lane, and it runs in CI. If a rebase rule ever overstepped, that
check fails.

**There are three first-party patches upstream does not have.** `0006` adds the
device-tree sound card that turns upstream's `0005` HDMI-RX audio codec into a
capturable ALSA card — without it the codec binds but `/proc/asound/cards` shows
no HDMI-RX capture card, because nothing in the tree binds the codec to a DAI.
`0006` adds `#sound-dai-cells` to `hdmi_receiver`, an `hdmirx-sound`
`simple-audio-card`, and enables it plus `i2s7_8ch` on both boards.

`0008` repairs `0001` rather than extending it: `rkvenc_dma_import_fd()` recorded
an imported dma-buf's length from the first mapped segment only, and `0001` never
set a DMA max segment size, so every import over 64 KiB was truncated to exactly
`0x10000` bytes. `0008` sets and reads back the cap in `rkvenc_hw_probe()`,
failing the probe if it did not take, and deliberately leaves the IOVA guardrail
that caught the symptom alone. Marked **`UNVALIDATED`** in
[`docs/UPSTREAM-STATUS.md`](docs/UPSTREAM-STATUS.md) — compiles into a real
kernel package; its runtime effect had never been observed on a board when it
was written.

`0009` is the other two-thirds of the same problem: Rockchip's MPP userspace
hard-codes a `system-uncached` dma-heap name mainline does not provide, so
`mpph264enc` failed to register at all, and MPP performs no CPU cache
maintenance on a heap it believes is uncached, so cached memory under that name
encoded non-deterministically. `0009` registers a second heap under exactly
that name — non-cacheable mappings, a one-time cache clean at allocation, and
skipped CPU-sync only for that heap — reusing the `system_heap.c` extension
point `system_cc_shared` already has. Also **`UNVALIDATED`**: the kernel's
cacheable linear-map alias of those pages is left in place, so getting the
cache handling subtly wrong yields silent intermittent corruption rather than
an error, and no compile can rule that out. What a real board must demonstrate
first: [`docs/BOARD-QUALIFICATION.md`](docs/BOARD-QUALIFICATION.md).

### Why not the `sfqr0414` fork

The `sfqr0414/rockchip-rk3588-mainline-patches` fork was evaluated and rejected:
stale (last push 2026-02-10, predates `0005`), v1-based VEPU580 patch (upstream
has since shipped v2 and v3), and hardware-untested with a machine-generated
history. Forking `rcawston` directly stays on the maintained line, with the
encoder patch at v3 and the audio patch present.

---

## Scope — what this repository does not do

It gates **patch application**. It does not:

- build a kernel, or produce any `.deb` or image artifact;
- verify the patched tree compiles;
- test anything on RK3588 hardware;
- compile or apply the device-tree overlay;
- claim the series is upstream-mergeable. It is a CeraLive-maintained adaptation,
  not a submission to `rcawston` or to the Linux kernel. Upstream's own README
  states the encoder driver is "not intended for upstream merge".

Kernel builds are the image pipeline's job.

---

## Licence and provenance

Read [`docs/PROVENANCE.md`](docs/PROVENANCE.md) before depending on this.

The new encoder sources carry `SPDX-License-Identifier: (GPL-2.0+ OR MIT)` and
`MODULE_LICENSE("Dual MIT/GPL")`. The Rockchip BSP originals they were ported from
carry the **same** SPDX tags — the dual-licence claim is inherited from the
copyright holder, not invented downstream. Distributing this as GPL-2.0 kernel
patches is the ordinary, safe case, and that is the basis of distribution here.

Caveat: the upstream patch repository has **no `LICENSE` file at all**, so there
is no collection-level grant, and no line-by-line derivation audit of the ~4,200
ported lines was performed. Anyone relying on the **MIT** branch of that
disjunction needs an independent audit and legal review. No legal sign-off is
claimed here — `docs/PROVENANCE.md` is a factual ledger, including its open
questions.

## Credits

`0001`–`0005` are the work of **Ross Cawston**
([`rcawston`](https://github.com/rcawston)), ported from Rockchip's BSP MPP
driver, and are carried here byte-for-byte. This fork contributes packaging,
pinning, auditing, and CI.

`0006`, `0008` and `0009` are first-party CeraLive work with no upstream
counterpart. `0006` is a device-tree change modelled on the Rockchip BSP's own
`hdmiin-sound` wiring (`rockchip,cpu = <&i2s7_8ch>`, receiver as clock master),
expressed with mainline's `simple-audio-card` instead of the BSP's `rockchip,hdmi`
machine driver. `0008` is a three-statement fix to the encoder driver `0001`
introduces, written against the pinned kernel's own DMA API. `0009` follows the
shape of the ACK/Rockchip uncached dma-heap, but is written against mainline's
`system_heap.c` and its existing per-heap drvdata mechanism rather than copied —
mainline has no `dma_heap_get_dev()`, so the one-time cache clean uses
`arch_dma_prep_coherent()`, the same primitive `dma_direct_alloc()` uses. All
three are kept in a separate `ceralive/` directory precisely so the credit line
above stays true.

`0007` is neither ours nor Ross Cawston's: it is a straight backport of a mainline
commit by Simon Xue, carried in `backports/` with its own provenance header.

`0010`, `0011` and `0012` are likewise other people's work — Shawn Lin
(Rockchip), Simon Wright, and Detlev Casanova (Collabora) — but taken from
postings that have **not** been merged. They carry a different provenance variant
for that reason: their headers say *"Backport of unmerged vN posting"* and claim
no commit id, because none exists. Each one's canonical mail is archived beside it
in `backports/lore/`, so the digest in its header can be recomputed offline. They
were imported by `scripts/import-lore-series.py` from the canonical lore thread
archive; none was transcribed by hand.
