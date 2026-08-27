# rk3588-kernel-patches

Out-of-tree mainline Linux patches for the Rockchip RK3588, packaged as a
**`git am`-able mailbox series** pinned to an exact kernel tag.

CeraLive fork of [`rcawston/rockchip-rk3588-mainline-patches`](https://github.com/rcawston/rockchip-rk3588-mainline-patches),
imported at `e13a311` (2026-07-01) with full history and authorship preserved.

| | |
|---|---|
| **Target kernel** | `v7.2` (`8d3ae59288f1e7d58d76558a6ee96d533bc5019f`) |
| **Why that kernel** | Armbian rk3588 `bleedingedge` → `KERNEL_MAJOR_MINOR=7.2` — derived in [`docs/PREFLIGHT.md`](docs/PREFLIGHT.md). Armbian itself still points that branch at `tag:v7.2-rc7`; we pin the **final** release deliberately. |
| **Boards** | Radxa Rock 5B+, Orange Pi 5+ (both `BOARDFAMILY=rockchip-rk3588`) |
| **Status** | **Re-anchored onto `v7.2`; all 24 active members `git am` clean and every post-apply assertion passes.** The first 22 members cross-compiled before `0028` was added; `0028` has since been built into a real v7.2 kernel and live-tested on a Rock 5B+, with a `MIXED` PR_SWAP result recorded in its row below. `0029` applies cleanly but its separate multi-cycle hardware reliability test has not run. The rebase ledger is [`docs/REBASE-v7.2.md`](docs/REBASE-v7.2.md). **Not upstream-bound.** Every completed board result this repo quotes was measured at the previous `v7.1.7` base and is historical here. |

## What's in the series

Upstream's numbering is preserved verbatim, gap included. First-party and
backported patches continue the same counter from `0006`. 24 members are active
across 29 slots: `0004` was never published, and `0007`, `0023`, `0024` and
`0025` are retired ordinals whose slots stay burned.

| | Patch | Source | What it does |
|---|---|---|---|
| `0001` | vepu580 encoder (v3) | `upstream/` | VEPU580 / RKVENC v2 H.265 · H.264 · JPEG hardware encoder, ported from the Rockchip BSP MPP driver. ~4,200 lines, 9 new files. |
| `0002` | hdmirx EDID fix (v1) | `upstream/` | Makes a written EDID actually visible to the HDMI source. |
| `0003` | hdmirx plugout fix (v1) | `upstream/` | Fixes a buffer overflow on repeated HDMI-RX replug. |
| *0004* | — | — | **Never published upstream.** The gap is intentional; do not renumber to close it. |
| `0005` | hdmirx audio | `upstream/` | The driver half of HDMI-RX audio capture: registers an ASoC `hdmi-audio-codec` under `hdmi_receiver@fdee0000` and drives the receiver's audio FIFO, ACR-derived sample rate and recovered clock. Adds no device tree. |
| `0006` | hdmirx audio sound card | `ceralive/` | The device-tree half. Without it `0005`'s codec is bound but ALSA never instantiates a card, so HDMI-IN audio cannot be captured at all. |
| *0007* | — | — | **Retired ordinal.** Was a `backports/` backport of mainline `8d4346ecd495`, the IOMMU `MMU_AUTO_GATING` fix. That commit is in the `v7.2` base, so carrying it twice is what the retirement avoids — the fix is still there, it just is not ours any more. Slot burned like `0004`'s: [`docs/UPSTREAM-STATUS.md` § retired ordinals](docs/UPSTREAM-STATUS.md#retired-ordinals-0007-0023-0024-0025); the archived file: [`retired/REGISTRY.md`](retired/REGISTRY.md). |
| `0008` | rkvenc DMA max segment size | `ceralive/` | **`UNVALIDATED` on hardware.** Sets the encoder's DMA max segment size in `rkvenc_hw_probe()`, so an imported dma-buf's recorded length stops being truncated to the `SZ_64K` default. Fixes a bookkeeping defect in `0001`; the IOVA guardrail that catches the symptom is deliberately left alone. |
| `0009` | `system-uncached` dma-heap | `ceralive/` | **`UNVALIDATED` on hardware.** Registers a second dma-heap named exactly `system-uncached` — the name Rockchip's MPP userspace hard-codes and mainline does not provide — with non-cacheable mappings, a one-time cache clean at allocation, and the CPU-sync steps skipped only for that heap. Without it `mpph264enc` does not register at all, and cached memory under an uncached name encodes non-deterministically. |
| `0010` | naneng-combphy RTERM erratum | `backports/` | **Unmerged lore posting** (`PATCHv1`, Shawn Lin). Forces RX-termination detect ready in `PHYREG26` so a PCIe peer's termination is seen at critical temperatures. No commit id exists and none is claimed. |
| `0011` | dw-hdmi-qp N/CTS helper | `backports/` | **Unmerged lore posting** (standalone `PATCHv3`, Simon Wright, `Reviewed-by`+`Tested-by`). Drops dw-hdmi-qp's private audio N/CTS table, which disagrees with the shared helper at several TMDS rates, for `drm_hdmi_acr_get_n_cts()`. |
| `0012` | dw-hdmi-qp audio `-EOPNOTSUPP` | `backports/` | **Unmerged lore posting** (`PATCHv1`, Detlev Casanova, two independent `Tested-by`). Stops the audio hooks returning `-ENODEV` with no mode set, which ASoC logs as a fault — hundreds of lines on an idle board, in the same dmesg buffer `0005`/`0006` are diagnosed from. |
| `0013` | rkvenc gated fault injection | `ceralive/` | **Test instrumentation, absent from production.** Three Kconfig symbols and six one-shot debugfs controls under `/sys/kernel/debug/rkvenc-test/`, each with a read-only `*_consumed` counter so a harness can tell a fault that fired from a knob the driver ignored. |
| `0014` | rkvenc teardown and unwind | `ceralive/` | Six defects in `0001`'s teardown: a session freed on the release drain's timeout path while the worker still uses it, that drain sleeping under the lock its own completion needs, a dangling CCU list entry into freed memory, `remove()` clearing almost nothing it published, a devm service torn down under open FDs, and a devm IRQ live across `remove()`. |
| `0015` | rkvenc resource errors | `ceralive/` | Six discarded return values in `0001`: clock, IOMMU and reset acquisition failures were logged and swallowed — turning a `-EPROBE_DEFER` into a permanently bound device with no clock — and `clk_prepare_enable()`, `pm_runtime_get_sync()`, `rkvenc_hw_finish()` and `rkvenc_hw_reset()` returns were thrown away. |
| `0016` | rkvenc ioctl bounds | `ceralive/` | Six UAPI bounds defects, the worst an **information disclosure**: `rkvenc_result()` located a read request's class by its start offset only, then copied the caller's own claimed size, reading past a `kmalloc`'d buffer into the kernel heap and handing it to userspace. Also wrap/underflow/alignment, a byte/element mismatch, and every failure collapsed to `-ENOMEM`. |
| `0017` | HDMI-RX audio lifecycle | `ceralive/` | Four defects in `0005`'s audio path: an ineffective `cancel_delayed_work()` against a self-rescheduling worker, an ASoC-card/`work_lock`/DAPM lock cycle, discarded `clk_set_rate()` returns, and a 768 kHz rate CEA-861 cannot produce. |
| `0018` | truthful dma-heap partial registration | `ceralive/` | Not a defect fix. `dma_heap_add()` has no removal counterpart at this base, so a failed second registration leaves the first heap live for the boot. This says so instead of hiding it, and adds an injection seam so the failure is reachable from KUnit. **No atomicity is claimed.** |
| `0019` | rkvenc worker lock context + dma-buf API | `ceralive/` | **Root-caused on a REAL Rock 5B+**, from a plain unfaulted encode under KASAN+LOCKDEP. A `struct mutex` taken inside `spin_lock_irqsave()`, and the *locked* dma-buf entry points called by a static importer that holds no `resv`. |
| `0020` | rkvenc service survives a single core's unbind | `ceralive/` | **Root-caused on a REAL Rock 5B+**, by fault injection. `0014`'s own service state machine had no path back to `LIVE`, so one core's transient unbind left `/dev/mpp_service` returning `-ENODEV` for the rest of the boot — after the core had re-probed successfully. |
| `0021` | rkvenc task, core and service lifecycle | `ceralive/` | **Root-caused on a REAL Rock 5B+**, over one continuous fault-injection and unbind session. Four defects in one lifecycle, in the order the board gave them up because each fix made the next reachable: `rkvenc_task_finish()` released unconditionally what `rkvenc_hw_run()` had already unwound (`bad unlock balance`, runtime-PM underflow); the worker then kept reading a task it had just freed (KASAN use-after-free); a secondary core stayed a dispatch target after a main-core rebind left its IOMMU domain NULL (Oops in `__iommu_attach_group()`); and a service-node unbind freed `srv` under an open descriptor, because its wait was skipped whenever a core had already claimed the quiesce. Carried as `0021`+`0023`+`0024`+`0025` while it was being discovered, folded into one patch afterwards — **byte-neutral**, proven by an identical `git am` tree object. |
| `0022` | rkvenc ioctl request coverage and element bounds | `ceralive/` | **Root-caused on a REAL Rock 5B+, then broken by it TWICE and amended in place both times; the current version is hardware-verified.** From an ioctl drill that `0016` should have made green and did not: a register request naming bytes no class owns was clamped and accepted instead of refused; `INIT_TRANS_TABLE` bounded bytes but not alignment; an unreadable user buffer reported `-EIO`. Reading the same paths found two unbounded counts and a byte/element overrun no drill case covers. v1's coverage test then refused **every** encode, and v2's refused **every H.265** one — MPP's HEVC programme is a single write spanning `SQI` and `SCL` across a genuine 24-byte hole in the class map, which "one contiguous run" cannot accept. The rule is now *clipping*: a span may cross the map's own holes provided it leaves no class half-named, which is exactly what `class-overrun` does and still gets `-EINVAL` for. |
| *0023*–*0025* | — | — | **Retired ordinals.** Carried while the `0021` lifecycle defects were being discovered one at a time, then folded into `0021`. The slots are burned like `0004`'s and `0007`'s, not renumbered. What each one individually documented: [`docs/UPSTREAM-STATUS.md` § retired ordinals](docs/UPSTREAM-STATUS.md#retired-ordinals-0007-0023-0024-0025); the archived files: [`retired/REGISTRY.md`](retired/REGISTRY.md). |
| `0026` | hdmirx register lock hardirq context | `ceralive/` | **Root-caused AND re-verified on a REAL Rock 5B+**, the first time a physical HDMI source was attached to a lockdep boot. `rst_lock` is a `spinlock_t` taken from the CEC and HDMI hardirqs, which `CONFIG_PROVE_RAW_LOCK_NESTING` reports as an invalid wait context — and that report calls `debug_locks_off()`, silencing lockdep for the rest of the boot in *every* subsystem. Promoted to `raw_spinlock_t`; same scope, same leaf position, identical code on a non-RT build. |
| `0027` | hdmirx SCDC bit-clock-ratio recovery | `ceralive/` | **Root-caused, fixed AND validated on a REAL Rock 5B+ in one session** — the first HDMI-RX patch here whose evidence is a working 4K60 capture. `hdmirx_tmds_clk_ratio_config()` cannot tell "the source declared 1/10" from "the source wrote no SCDC at all", so an empty `SCDC_REGBANK_STATUS1` was treated as authoritative and a 4K59.94p link was structurally unlockable — ~500+ consecutive failures — with `0002`'s PHY re-init unable to help, because it ends by re-deriving the ratio from that same empty register. Fixes the failure log too: it named `SCDC_REGBANK_STATUS3`, the wrong register, and never printed `cmu_st`. After a completed lock-loop failure the ratio is forced to 1/40 once and the wait re-entered; the flag clears on `hdmirx_plugout()`. **600/600 frames at 3840x2160, steady 59.94 fps, zero errors, 4/4 across HPD renegotiation cycles.** Answers `docs/EVAL-0002-EDID.md` B4 in the negative. |
| `0028` | Rock 5B+ Type-C dual-role-power PDOs | `ceralive/` | **Live root cause captured, then live-tested on a REAL Rock 5B+ against the patched v7.2 kernel — the PDO change itself is proven; the PR_SWAP it enables is `MIXED`, not clean-accepted.** Adds `PDO_FIXED_DUAL_ROLE` to the fixed sink and source PDOs in the Rock 5B+/5T connector so TCPM may put a PR_SWAP request on the wire. The peer Osmo already advertised the capability as `[RUD]`; the Rock exposed read-only `dual_role_power=0` and rejected locally with zero PD traffic. On the patched kernel `dual_role_power` reads `1` on both capability records, and a real `AMS POWER_ROLE_SWAP` reaches the wire. Two live replicates against a DJI Osmo Pocket 3 disagreed: the first was **accepted by the camera** and then **timed out** in the electrical handoff at the 920 ms guard (`ERROR_RECOVERY` → `PORT_RESET`, back to sink, camera USB device gone); the second **fully succeeded** — the Rock became source, `VBUS on`, and the camera negotiated and was granted 5 V / 3 A (capped 2000/2000 mA), confirmed by `power_role: [source]` and the `vbus5v0_typec` regulator `enabled`. One failure in two replicates is `TYPEC_PRSWAP: MIXED` under the campaign's pre-registered zero-failure rule: capable, not reliable. **Still open and undiagnosed:** after the successful swap the camera's USB *data* link dropped once ~10 s in and did not auto-recover, while the power layer stayed stable throughout. Evidence comes from a manually test-built kernel, so nothing here makes the patch a shipped default. Edge-track and Rock-only: Orange Pi, vendor 6.1, every non-PDO property and every other PDO flag remain untouched. The formal drill harness has since run to a real `RUN_COMPLETE` (run_uuid `68704060-…`) and **disagreed with the manual pass**: it scored PR_SWAP `REJECTED` **2 of 2** replicates, both `printf: write error: Protocol error` (EPROTO) on the `power_role` write, alongside `TYPEC_PEER: MIXED` / `TYPEC_DRSWAP: WORKS` / `TYPEC_CHARGE: BOARD_SOURCES_OK`. Session-wide the tally is **4 attempts: 1 success, 1 timeout, 2 rejected** — so the verdict stays `MIXED`/fragile rather than becoming a clean reject. **Correlated, causation not established:** both rejections landed at the exact dmesg timestamp of a full XHCI teardown matching the pre-existing F19 CC-line dropout signature, which was already known to fire spontaneously at idle; the fix that would have been the obvious candidate (`usb: typec: fusb302: cache PD RX state`, `1e61f6ab08786d`) is already in the pinned `v7.2` base, and there is no DT or module knob for the TCPM CC debounce. See [`docs/UPSTREAM-STATUS.md`](docs/UPSTREAM-STATUS.md) § `0028` for the full evidence and the outstanding `dyndbg` follow-up. |
| `0029` | Rock 5B+ Type-C Try.SRC preference | `ceralive/` | **Patch application proven; charging reliability not yet tested.** The pinned v7.2 ground truth is a board-target override in `rk3588-rock-5b-plus.dts`: `&usb_con` keeps `power-role = "dual"` and sets `try-power-role = "sink"`. A same-camera, same-policy board A/B found the sink-preferring Rock charging only intermittently, with repeated `SNK_WAIT_CAPABILITIES_TIMEOUT`, while the Orange Pi's own pre-existing source preference settled immediately as source/host and charged reliably on first attach. This patch changes only that existing Rock 5B+ override to `try-power-role = "source"`. Try.SRC is a soft preference within normal CC-toggle detection, not the hard `port_type=source` FORCE_SOURCE pin that skipped the handshake and broke camera attachment 3/3. The port remains dual-role; `power-role`, `data-role`, connector/FUSB302 status, `0028`'s PDOs, Rock 5B/5T, Orange Pi and vendor 6.1 are untouched. Whether this makes charging reliable is deliberately open until the separate multi-cycle hardware test runs. |

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

Several members carry an **`UNVALIDATED`** marker — `0008` and `0009` on Orange Pi
5+, and the whole `0013`–`0022` + `0026` block to varying degrees. `0027` is the
exception that shows what clearing one looks like: it landed already validated,
with a 600-frame 4K59.94p capture behind it. What a real board has to
demonstrate before a marker comes off — every leg, every command, on both boards —
is [`docs/BOARD-QUALIFICATION.md`](docs/BOARD-QUALIFICATION.md), and what is
already proven, per patch, is the **Last checked** column in
[`docs/UPSTREAM-STATUS.md`](docs/UPSTREAM-STATUS.md).

**A patch being landed is not a patch being verified.** `0015` and `0016` were both
ticked before anything ran on hardware, and the first real drill against them
failed — `0021` and `0022` are what came out of that, and `0021` alone is four
defects deep, because fixing the bug that aborts an error path is how you find the
bugs further down it. Read the marker, not the merge.

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
family. For `bleedingedge` on rk3588 the family directory is `rockchip64-7.2`:

```bash
git clone --depth 1 https://github.com/armbian/build
mkdir -p build/userpatches/kernel/archive/rockchip64-7.2/
cp patches/*.patch build/userpatches/kernel/archive/rockchip64-7.2/
cd build && ./compile.sh BOARD=rock-5b-plus BRANCH=bleedingedge
```

Do not copy `patches/series` into that directory — Armbian would try to apply it
as a patch.

> **That last line may not run as written, and that is expected.** Neither
> CeraLive board lists `bleedingedge` in its `KERNEL_TARGET` menu
> (`rock-5b-plus` = `vendor,current,edge`, `orangepi5-plus` =
> `current,edge,vendor`), so `compile.sh` may refuse the branch. That costs this
> repository nothing: the family directory above is what the series needs, and
> CeraLive builds `KERNEL_TAG` from source through `image-building-pipeline`
> rather than through Armbian's board menu. `scripts/preflight.sh` prints those
> two values and deliberately does not fail on them — see
> [`docs/PREFLIGHT.md`](docs/PREFLIGHT.md).

> The family directory is derived, not guessed. It comes from
> `KERNEL_MAJOR_MINOR=7.2` + `LINUXFAMILY=rockchip64`; see
> [`docs/PREFLIGHT.md`](docs/PREFLIGHT.md). Upstream's README says
> `rockchip64-6.19`, which was right for the kernel *they* targeted.

---

## Changing the kernel pin

`kernel-pin.env` is the single source of truth. Bumping it is a deliberate act:

```bash
scripts/preflight.sh --head     # has Armbian moved the branch we pin?
# edit KERNEL_TAG / KERNEL_TAG_OBJECT / KERNEL_COMMIT together
cp rebase/v7.2.rules rebase/<new-tag>.rules     # seed, then re-decide every rule
scripts/apply.sh                # resolve conflicts per the rule below
# then write docs/REBASE-<new-tag>.md — a verdict per ordinal, hunks for every revision
```

A member whose fix the new base already carries is **retired**, not deleted: move
it to [`retired/`](retired/REGISTRY.md), add its row, and leave the ordinal burned.
That is what happened to `0007` at `v7.2`.

**The rule for conflicts.** `rebase/*.rules` are context-only for ALL lanes. At a base bump, `ceralive/`-lane patches MAY be revised in place (payload changes) to preserve their documented intent on the new base; every such revision is recorded hunk-by-hunk in `docs/REBASE-<tag>.md` with an intent-preservation note, and is verified by the post-apply assertions and the bump's compile evidence. Payload drift in `upstream/` or `backports/` lanes remains behavioural: resolve ONLY by a new `ceralive/` fixup patch at a fresh ordinal (the 0008-fixes-0001 pattern) or STOP and report. `upstream/` bytes are never edited.

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

**The series is re-anchored for `v7.2`.** Upstream targeted `v6.19-rc8`. Each base
move gets its own ledger, and the current one is
[`docs/REBASE-v7.2.md`](docs/REBASE-v7.2.md): a verdict per ordinal, the reverse/
forward apply probes behind it, and every revised hunk with the intent it
preserves. Two members needed work at this base — `0009` was adapted to `v7.2`'s
modularised system heap, and `0018`'s added note re-cites the base's own
no-unload statement — while `0007` was retired outright because `8d4346ecd495` is
in the base. Everything else applies unchanged. The two earlier ledgers,
[`docs/REBASE-v7.1.7.md`](docs/REBASE-v7.1.7.md) and
[`docs/REBASE-v7.1.5.md`](docs/REBASE-v7.1.5.md), are kept as the record of the
bases before this one.

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

`0007` was neither ours nor Ross Cawston's: it was a straight backport of a
mainline commit by Simon Xue, carried in `backports/` with its own provenance
header until the `v7.2` base absorbed the commit. It is archived in `retired/`,
credit intact.

`0010`, `0011` and `0012` are likewise other people's work — Shawn Lin
(Rockchip), Simon Wright, and Detlev Casanova (Collabora) — but taken from
postings that have **not** been merged. They carry a different provenance variant
for that reason: their headers say *"Backport of unmerged vN posting"* and claim
no commit id, because none exists. Each one's canonical mail is archived beside it
in `backports/lore/`, so the digest in its header can be recomputed offline. They
were imported by `scripts/import-lore-series.py` from the canonical lore thread
archive; none was transcribed by hand.
