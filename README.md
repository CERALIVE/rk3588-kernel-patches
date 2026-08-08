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
| **Status** | Applies cleanly. **Not built, not run on hardware, not upstream-bound.** |

## What's in the series

Upstream's numbering is preserved verbatim, gap included. First-party patches
continue the same counter from `0006`:

| | Patch | Source | What it does |
|---|---|---|---|
| `0001` | vepu580 encoder (v3) | `upstream/` | VEPU580 / RKVENC v2 H.265 · H.264 · JPEG hardware encoder, ported from the Rockchip BSP MPP driver. ~4,200 lines, 9 new files. |
| `0002` | hdmirx EDID fix (v1) | `upstream/` | Makes a written EDID actually visible to the HDMI source. |
| `0003` | hdmirx plugout fix (v1) | `upstream/` | Fixes a buffer overflow on repeated HDMI-RX replug. |
| *0004* | — | — | **Never published upstream.** The gap is intentional; do not renumber to close it. |
| `0005` | hdmirx audio | `upstream/` | The driver half of HDMI-RX audio capture: registers an ASoC `hdmi-audio-codec` under `hdmi_receiver@fdee0000` and drives the receiver's audio FIFO, ACR-derived sample rate and recovered clock. Adds no device tree. |
| `0006` | hdmirx audio sound card | `ceralive/` | The device-tree half. Without it `0005`'s codec is bound but ALSA never instantiates a card, so HDMI-IN audio cannot be captured at all. |

Plus [`overlays/rockchip-rk3588-rkvenc-mpp.dts`](overlays/rockchip-rk3588-rkvenc-mpp.dts),
the device-tree overlay the encoder needs, carried verbatim.

Which of these have an upstream counterpart, how far along it is, and what would
have to be true before a patch can be dropped, is tracked per patch in
[`docs/UPSTREAM-STATUS.md`](docs/UPSTREAM-STATUS.md).

## Layout

```
upstream/          Ross Cawston's original diff -ruN files, byte-for-byte
ceralive/          first-party patches with no upstream counterpart
backports/         patches taken from mainline / a stable tree / lore
retired/           patches moved out of the series, byte-unchanged, + REGISTRY.md
patches/           the git-am series — GENERATED from the lanes, never hand-edit
overlays/          the rkvenc/MPP device-tree overlay
rebase/            per-kernel-tag context re-anchor rules
scripts/           preflight · build-series · verify-payload-parity · apply
kernel-pin.env     every pinned coordinate, in one sourceable file
docs/              provenance audit · rebase ledger · preflight derivation · upstream status
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
context anchors drifted in between; both were re-anchored, and all five series
members are documented hunk by hunk in
[`docs/REBASE-v7.1.7.md`](docs/REBASE-v7.1.7.md). The earlier
[`docs/REBASE-v7.1.5.md`](docs/REBASE-v7.1.5.md) is kept as the record of the
previous base.

**Nothing the patches do was changed.** `scripts/verify-payload-parity.py` proves
that the set of added and removed lines in `patches/` is byte-identical to the
patch's source lane, and it runs in CI. If a rebase rule ever overstepped, that
check fails.

**There is one first-party patch upstream does not have.** `0006` adds the
device-tree sound card that turns upstream's `0005` HDMI-RX audio codec into a
capturable ALSA card. Upstream `0005` is driver-only; on a Rock 5B+ running the
full series the codec device is bound with no cable attached
(`/sys/devices/platform/fdee0000.hdmi_receiver/hdmi-audio-codec.7.auto`) while
`/proc/asound/cards` shows no HDMI-RX capture card, because nothing in the device
tree binds that codec to a DAI. `0006` adds `#sound-dai-cells` to
`hdmi_receiver`, adds an `hdmirx-sound` `simple-audio-card`, and enables it plus
`i2s7_8ch` on the two CeraLive boards. It lives in `ceralive/`, is clearly marked
first-party in its own mail header, and carries no upstream attribution.

### Why not the `sfqr0414` fork

There is another public fork, `sfqr0414/rockchip-rk3588-mainline-patches`, which
repackages the driver as a DKMS module. This fork does not use it, for three
reasons:

- **Stale.** Last push 2026-02-10. Upstream has moved since — most importantly
  `0005` (HDMI-RX audio), added 2026-07-01, does not exist there at all. HDMI-RX
  audio capture is directly relevant to CeraLive.
- **v1-based.** It forked at upstream's `f9f342e` ("first commit"), which carried
  the **v1** VEPU580 patch. Upstream has since shipped v2 and v3, and its own
  commit `0959558` is titled "fix dts and update encoder patch". The `sfqr0414`
  tree never picked those up.
- **Hardware-untested, and largely machine-generated.** Its history
  (`Initial plan` → `Extract driver files…` → `Add compat.h, Makefile, dkms.conf…`
  → `Complete documentation…`, merged from a `copilot/…` branch) shows an
  automated extraction. No evidence of validation on an RK3588 board exists.

Forking `rcawston` directly stays on the maintained line, with the encoder patch
at v3 and the audio patch present.

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

`0006` is first-party CeraLive work with no upstream counterpart: a device-tree
change modelled on the Rockchip BSP's own `hdmiin-sound` wiring
(`rockchip,cpu = <&i2s7_8ch>`, receiver as clock master), expressed with mainline's
`simple-audio-card` instead of the BSP's `rockchip,hdmi` machine driver. It is
kept in a separate `ceralive/` directory precisely so the credit line above stays
true.
