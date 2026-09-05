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
| **Status** | **31 active members across 49 slots**, gated by `scripts/apply.sh` on `v7.2`. Nine byte-verified members carry `rk3588-media-island v2026.9.2`. HDMI-RX audio now uses unmerged upstream v4 plus four first-party deltas. This audio migration is code-only: no new image or board evidence is claimed. |

## What's in the series

New member `0040` refuses EDID writes and clears with `-EBUSY` while capture
streams, before any HPD or EDID mutation. Idle writes remain unchanged.
Hardware acceptance is deferred to the
[EDID guard board procedure](docs/EDID-STREAMING-GUARD.md).

New member `0041` stops the capture format claiming sRGB for every source. The
AVI InfoFrame's colorimetry, extended colorimetry and both quantization fields
were already unpacked and thrown away; they are now mapped to V4L2 by one pure
function whose every table row is asserted in
[`tests/test_hdmirx_avi_colorimetry.py`](tests/test_hdmirx_avi_colorimetry.py).
Members `0042`–`0045` import HDMI-RX audio v4, byte-preserved with canonical
lore provenance. `0046`–`0049` preserve clock-error handling, safe worker
teardown, multichannel routing and Rock 5B+ enablement. The shared ALSA card is
named exactly **`RK3588 HDMI-IN`**. The v4 second-suspend-cycle silence remains
unfixed; jack notifications and idle pre-lock polling are deliberately retired.
See the [per-behavior ledger](docs/UPSTREAM-STATUS.md#hdmi-rx-audio-v4-reconciliation--2026-09-05)
for the behavior trade-offs and evidence. The series now has 31 active members
across 49 slots.

Upstream's numbering is preserved verbatim, gap included. First-party,
backported, and island patches continue the same counter. 31 members are active
across 49 slots: `0004` was never published, and seventeen retired ordinals stay
burned.

| | Patch | Source | What it does |
|---|---|---|---|
| *0001* | retired vepu580 encoder (v3) | `retired/` | Historical standalone-rkvenc import; superseded by `rk3588-media-island v2026.9.0` and archived byte-unchanged. |
| `0002` | hdmirx EDID fix (v1) | `upstream/` | Makes a written EDID actually visible to the HDMI source. |
| `0003` | hdmirx plugout fix (v1) | `upstream/` | Fixes a buffer overflow on repeated HDMI-RX replug. |
| *0004* | — | — | **Never published upstream.** The gap is intentional; do not renumber to close it. |
| *0005* | retired hdmirx audio | `retired/` | Replaced by v4 plus explicit behavior deltas; Ross Cawston's source remains byte-unchanged. |
| *0006* | retired hdmirx audio sound card | `retired/` | Replaced by v4 shared one-cell DAI card plus Rock enablement in 0049. |
| *0007* | — | — | **Retired ordinal.** Was a `backports/` backport of mainline `8d4346ecd495`, the IOMMU `MMU_AUTO_GATING` fix. That commit is in the `v7.2` base, so carrying it twice is what the retirement avoids — the fix is still there, it just is not ours any more. Slot burned like `0004`'s: [`docs/UPSTREAM-STATUS.md` § retired ordinals](docs/UPSTREAM-STATUS.md#retired-ordinals-0007-0023-0024-0025); the archived file: [`retired/REGISTRY.md`](retired/REGISTRY.md). |
| *0008* | retired rkvenc DMA max segment size | `retired/` | Historical standalone-rkvenc fix; intent is re-expressed and tested in the island. |
| `0009` | `system-uncached` dma-heap | `ceralive/` | Registers the exact heap name Rockchip MPP userspace requires. Its v7.1.7 board validation is historical at this v7.2 base. |
| `0010` | naneng-combphy RTERM erratum | `backports/` | **Unmerged lore posting** (`PATCHv1`, Shawn Lin). Forces RX-termination detect ready in `PHYREG26` so a PCIe peer's termination is seen at critical temperatures. No commit id exists and none is claimed. |
| `0011` | dw-hdmi-qp N/CTS helper | `backports/` | **Unmerged lore posting** (standalone `PATCHv3`, Simon Wright, `Reviewed-by`+`Tested-by`). Drops dw-hdmi-qp's private audio N/CTS table, which disagrees with the shared helper at several TMDS rates, for `drm_hdmi_acr_get_n_cts()`. |
| `0012` | dw-hdmi-qp audio `-EOPNOTSUPP` | `backports/` | **Unmerged lore posting** (`PATCHv1`, Detlev Casanova, two independent `Tested-by`). Stops the audio hooks returning `-ENODEV` with no mode set, which ASoC logs as a fault — hundreds of lines on an idle board, in the same dmesg buffer `0005`/`0006` are diagnosed from. |
| *0013–0016* | retired rkvenc instrumentation and hardening | `retired/` | Historical standalone-rkvenc intents, re-expressed as island source plus permanent fault and boundary tests. |
| *0017* | retired HDMI-RX audio lifecycle | `retired/` | Clock/rate and lifecycle intents reworked against v4 by 0046–0048. Historical fault controls remain in the archive. |
| `0018` | truthful dma-heap partial registration | `ceralive/` | Not a defect fix. `dma_heap_add()` has no removal counterpart at this base, so a failed second registration leaves the first heap live for the boot. This says so instead of hiding it, and adds an injection seam so the failure is reachable from KUnit. **No atomicity is claimed.** |
| *0019–0022* | retired rkvenc concurrency, lifecycle and UAPI hardening | `retired/` | Historical board-found standalone-rkvenc fixes; the island fault campaign maps each intent to imported or CeraLive source and mutation evidence. |
| *0023*–*0025* | — | — | **Retired ordinals.** Carried while the `0021` lifecycle defects were being discovered one at a time, then folded into `0021`. The slots are burned like `0004`'s and `0007`'s, not renumbered. What each one individually documented: [`docs/UPSTREAM-STATUS.md` § retired ordinals](docs/UPSTREAM-STATUS.md#retired-ordinals-0007-0023-0024-0025); the archived files: [`retired/REGISTRY.md`](retired/REGISTRY.md). |
| `0026` | hdmirx register lock hardirq context | `ceralive/` | **Root-caused AND re-verified on a REAL Rock 5B+**, the first time a physical HDMI source was attached to a lockdep boot. `rst_lock` is a `spinlock_t` taken from the CEC and HDMI hardirqs, which `CONFIG_PROVE_RAW_LOCK_NESTING` reports as an invalid wait context — and that report calls `debug_locks_off()`, silencing lockdep for the rest of the boot in *every* subsystem. Promoted to `raw_spinlock_t`; same scope, same leaf position, identical code on a non-RT build. |
| `0027` | hdmirx SCDC bit-clock-ratio recovery | `ceralive/` | **Root-caused, fixed AND validated on a REAL Rock 5B+ in one session** — the first HDMI-RX patch here whose evidence is a working 4K60 capture. `hdmirx_tmds_clk_ratio_config()` cannot tell "the source declared 1/10" from "the source wrote no SCDC at all", so an empty `SCDC_REGBANK_STATUS1` was treated as authoritative and a 4K59.94p link was structurally unlockable — ~500+ consecutive failures — with `0002`'s PHY re-init unable to help, because it ends by re-deriving the ratio from that same empty register. Fixes the failure log too: it named `SCDC_REGBANK_STATUS3`, the wrong register, and never printed `cmu_st`. After a completed lock-loop failure the ratio is forced to 1/40 once and the wait re-entered; the flag clears on `hdmirx_plugout()`. **600/600 frames at 3840x2160, steady 59.94 fps, zero errors, 4/4 across HPD renegotiation cycles.** Answers `docs/EVAL-0002-EDID.md` B4 in the negative. |
| `0028` | Rock 5B+ Type-C dual-role-power PDOs | `ceralive/` | **Live root cause captured, then live-tested on a REAL Rock 5B+ against the patched v7.2 kernel — the PDO change itself is proven; the PR_SWAP it enables is `MIXED`, not clean-accepted.** Adds `PDO_FIXED_DUAL_ROLE` to the fixed sink and source PDOs in the Rock 5B+/5T connector so TCPM may put a PR_SWAP request on the wire. The peer Osmo already advertised the capability as `[RUD]`; the Rock exposed read-only `dual_role_power=0` and rejected locally with zero PD traffic. On the patched kernel `dual_role_power` reads `1` on both capability records, and a real `AMS POWER_ROLE_SWAP` reaches the wire. Two live replicates against a DJI Osmo Pocket 3 disagreed: the first was **accepted by the camera** and then **timed out** in the electrical handoff at the 920 ms guard (`ERROR_RECOVERY` → `PORT_RESET`, back to sink, camera USB device gone); the second **fully succeeded** — the Rock became source, `VBUS on`, and the camera negotiated and was granted 5 V / 3 A (capped 2000/2000 mA), confirmed by `power_role: [source]` and the `vbus5v0_typec` regulator `enabled`. One failure in two replicates is `TYPEC_PRSWAP: MIXED` under the campaign's pre-registered zero-failure rule: capable, not reliable. **Still open and undiagnosed:** after the successful swap the camera's USB *data* link dropped once ~10 s in and did not auto-recover, while the power layer stayed stable throughout. Evidence comes from a manually test-built kernel, so nothing here makes the patch a shipped default. Edge-track and Rock-only: Orange Pi, vendor 6.1, every non-PDO property and every other PDO flag remain untouched. The formal drill harness has since run to a real `RUN_COMPLETE` (run_uuid `68704060-…`) and **disagreed with the manual pass**: it scored PR_SWAP `REJECTED` **2 of 2** replicates, both `printf: write error: Protocol error` (EPROTO) on the `power_role` write, alongside `TYPEC_PEER: MIXED` / `TYPEC_DRSWAP: WORKS` / `TYPEC_CHARGE: BOARD_SOURCES_OK`. Session-wide the tally is **4 attempts: 1 success, 1 timeout, 2 rejected** — so the verdict stays `MIXED`/fragile rather than becoming a clean reject. **Correlated, causation not established:** both rejections landed at the exact dmesg timestamp of a full XHCI teardown matching the pre-existing F19 CC-line dropout signature, which was already known to fire spontaneously at idle; the fix that would have been the obvious candidate (`usb: typec: fusb302: cache PD RX state`, `1e61f6ab08786d`) is already in the pinned `v7.2` base, and there is no DT or module knob for the TCPM CC debounce. See [`docs/UPSTREAM-STATUS.md`](docs/UPSTREAM-STATUS.md) § `0028` for the full evidence and the outstanding `dyndbg` follow-up. |
| `0029` | Rock 5B+ Type-C Try.SRC preference | `ceralive/` | **Patch application proven, then live-tested on a REAL Rock 5B+ against the patched v7.2 kernel: every observed attach cycle landed the board as source, zero failures.** The pinned v7.2 ground truth is a board-target override in `rk3588-rock-5b-plus.dts`: `&usb_con` keeps `power-role = "dual"` and sets `try-power-role = "sink"`. A same-camera, same-policy board A/B found the sink-preferring Rock charging only intermittently, with repeated `SNK_WAIT_CAPABILITIES_TIMEOUT`, while the Orange Pi's own pre-existing source preference settled immediately as source/host and charged reliably on first attach. This patch changes only that existing Rock 5B+ override to `try-power-role = "source"`. Try.SRC is a soft preference within normal CC-toggle detection, not the hard `port_type=source` FORCE_SOURCE pin that skipped the handshake and broke camera attachment 3/3. The port remains dual-role; `power-role`, `data-role`, connector/FUSB302 status, `0028`'s PDOs, Rock 5B/5T, Orange Pi and vendor 6.1 are untouched. **Hardware result, 2026-08-27.** After a RAUC deploy and boot of the patched kernel, `/sys/class/typec/port0/preferred_role` read `source` where it read `sink` before — the DT change taking effect, proven independently of any camera behaviour. One fully instrumented attach then produced a textbook-clean source contract: `TOGGLING → SRC_ATTACH_WAIT → SRC_ATTACHED`, `VBUS on`, capabilities offered, the Osmo Pocket 3 requesting `5000 mV, 3000 mA for 2000/2000 mA`, `SRC_NEGOTIATE_CAPABILITIES → SRC_TRANSITION_SUPPLY → SRC_READY` with no reset, timeout or reject, and the `vbus5v0_typec` regulator `enabled`. Multiple further operator-driven unplug/replug cycles were polled live, and every `PRESENT` sample read `power_role: [source] sink` / `data_role: [host] device`; the operator reported every cycle working, with no failure observed. That is a decisive improvement on the pre-patch MIXED/mostly-sink baseline in `0028`'s row above, though it is a qualitative multi-cycle result, not a guarantee. **What could not be measured:** this board carries no VBUS current sense — no INA2xx-class part on the i2c bus, and the FUSB302 is a CC-line PD controller with no VBUS ADC — so the `tcpm_source_psy_4_0022` hwmon `curr1_input`/`in0_input` nodes read `0` even mid-contract and are unpopulated stubs. The evidence here is therefore protocol-level (VBUS enabled, PD contract accepted, regulator enabled) and no delivered wattage figure exists to quote. **Open, unconfirmed:** the operator saw no charging icon on the camera during the session, and offered the plausible explanation that its battery was already at or near full — plausible, not independently verified, and recorded as an open detail rather than a finding. Measured on a manually test-built edge kernel; nothing here makes `0029` a shipped default, and the vendor 6.1 track gains none of this. |
| `0030` | Orange Pi 5 Plus Type-C dual-role-power PDOs | `ceralive/` | **Clean PASS, confirmed on a REAL Orange Pi 5 Plus against the patched v7.2 kernel.** `0030` adds `PDO_FIXED_DUAL_ROLE` to the existing 5 V / 1.4 A source and 5 V / 10 mA sink declarations; both `dual_role_power` values read `1` after deployment. On the still-booted patched slot A, the operator performed a real USB-C detach/reattach lasting at least 10 seconds. The camera re-enumerated cleanly as `2ca3:0023` (`DJIPocket3`); `port_type` stayed `[dual]`; natural DRP arbitration settled `power_role=source` and `data_role=host` through the adaptive policy, with journal line `port0 settled as power_role=source data_role=host — no data-role swap needed` and zero manual role commands. `v4l2-ctl` confirmed live `/dev/video6`, `/dev/video7` and `/dev/media3` nodes, and the PDO capability fix remained intact (`dual_role_power=1` on both source and sink) after the cycle. The earlier post-boot camera absence was a transient camera/cable-side state, not a kernel or Type-C regression introduced by `0030`; the patch is confirmed compatible with normal camera operation. This remains Orange-Pi-only and edge-v7.2-only; no PR_SWAP behavior or reliability is claimed.** |
| `0031` | media-island maintained source | `island/` | Squashed create-mode patch for the MPP and multi_rga maintained source and UAPI. |
| `0032` | video build hooks | `island/` | Hooks the island MPP and multi_rga Kconfig and Makefiles into Linux. |
| `0033` | Rockchip IOMMU provider exports | `island/` | Exposes the real provider controls required by MPP and RGA. |
| `0034` | IOMMU DMA IOVA accessor | `island/` | Exposes the media IOVA allocation helpers used by the island. |
| `0035` | MPP encoder DT nodes | `island/` | Adds `mpp_srv`, `rkvenc_ccu`, both RKVENC2 cores, and their IOMMUs in-tree. |
| `0036` | MPP decoder DT ownership | `island/` | Hands `vdec0/1` to RKVDEC2 with the sole vendor compatible and adds `rkvdec_ccu`. |
| `0037` | MPP JPEG decoder DT node | `island/` | Adds the island-owned `jpegd` client and IOMMU in-tree. |
| `0038` | RGA3 DT ownership | `island/` | Hands RGA3 core0/core1 to multi_rga with sole `rockchip,rga3_core0` / `rockchip,rga3_core1` compatibles. |
| `0039` | RGA2 DT ownership | `island/` | Hands RGA2 to multi_rga with sole `rockchip,rga2_core0` compatible. |
| `0040` | streaming EDID guard | `ceralive/` | Refuses S_EDID writes and clears while capture streams, before mutation. |
| `0041` | AVI colorimetry on the capture format | `ceralive/` | Reports the source's colorimetry, encoding, transfer function and quantization instead of a hardcoded sRGB. The mapping is one pure function, asserted row by row off-hardware. |

Which of these have an upstream counterpart, how far along it is, and what would
have to be true before a patch can be dropped, is tracked per patch in
[`docs/UPSTREAM-STATUS.md`](docs/UPSTREAM-STATUS.md).

| Member | Source | Audio migration role |
|---|---|---|
| `0042` | `backports/` | v4 1/4: DAI binding |
| `0043` | `backports/` | v4 2/4: capture-only codec, ACR recovery, FIFO worker and suspend handling |
| `0044` | `backports/` | v4 3/4: shared RK3588 HDMI-IN card |
| `0045` | `backports/` | v4 4/4: Orange Pi enablement |
| `0046` | `ceralive/` | Clock-error propagation and LPCM rate validation |
| `0047` | `ceralive/` | Disarm/drain before EDID, cable-pull and removal |
| `0048` | `ceralive/` | Channel routing, invalid-rate backoff and retained AVI IRQ definition |
| `0049` | `ceralive/` | Rock family enablement and codec Kconfig closure |

Where an upstream counterpart was evaluated as a replacement and the answer was
written down, the verdict gets its own document. So far:

- [`docs/EVAL-0002-EDID.md`](docs/EVAL-0002-EDID.md) — keeps `0002`, and explains
  why the 7.2-rc1 EDID fix is not a substitute for it (it is already in the base,
  and it fixes something else).
- [`docs/EVAL-0005-AUDIO.md`](docs/EVAL-0005-AUDIO.md) — historical KEEP verdict;
  superseded by the audio v4 reconciliation ledger. The trade-offs it identified
  are now explicitly retired, reworked or retained, never silently assumed fixed.

Historical board evidence remains in [`docs/BOARD-QUALIFICATION.md`](docs/BOARD-QUALIFICATION.md)
with its measured kernel base. The island release has its own source, CI, and board
qualification contract; importing its mailbox is provenance work, not a new claim
that its runtime behavior has already shipped.

## Layout

```
upstream/          Ross Cawston's original diff -ruN files, byte-for-byte
ceralive/          first-party patches with no upstream counterpart
backports/         patches taken from mainline / a stable tree / lore
backports/lore/    canonical mail of each unmerged posting, one directory per candidate
island/            byte-preserved rk3588-media-island release mailboxes
tests/             stdlib unittest fixtures for the Python tooling
retired/           patches moved out of the series, byte-unchanged, + REGISTRY.md
patches/           the git-am series — GENERATED from the lanes, never hand-edit
rebase/            per-kernel-tag context re-anchor rules
scripts/           preflight · build-series · payload/release provenance checks · apply
kernel-pin.env     every pinned coordinate, in one sourceable file
docs/              provenance audit · rebase ledger · preflight derivation · upstream status · adopt-or-keep verdicts
```

All four source lanes run through the same converter, so `patches/` stays 100 %
generated. `verify-payload-parity.py` holds every patch to its lane payload, while
`verify-island-provenance.py` separately verifies the published asset SHA-256 and
byte-compares each `island/` member. The build refuses any lane file not accounted
for exactly once.

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

The island MPP service and multi_rga modules are selectable independently. The
first island release compiles exactly RKVENC2, RKVDEC2 and JPGDEC as MPP clients.

```bash
./scripts/config --module CONFIG_ROCKCHIP_MPP_SERVICE
./scripts/config --enable CONFIG_ROCKCHIP_MPP_RKVENC2
./scripts/config --enable CONFIG_ROCKCHIP_MPP_RKVDEC2
./scripts/config --enable CONFIG_ROCKCHIP_MPP_JPGDEC
./scripts/config --module CONFIG_ROCKCHIP_MULTI_RGA
```

### Then: device tree

The MPP encoder, decoder and JPEG nodes are integrated directly into
`rk3588-base.dtsi` by `0035`–`0037`, so both supported board DTBs inherit them.
The retired standalone-rkvenc overlay is not part of the active series.

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
main reason this fork exists — `patches/` is generated from all four source lanes
by `scripts/build-series.py`, which adds the consumer's mailbox headers and drops
the `.DS_Store` noise from the old imported files.

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

**The retained first-party patches answer gaps upstream does not.** `0049` enables
v4's shared HDMI-IN card and `i2s7_8ch` on the Rock family, which upstream 4/4
does not cover. The old 0006 two-board wiring is archived, not co-applied with
the incompatible one-cell binding.

The historical standalone-rkvenc `0008` and its associated hardening patches are
archived byte-unchanged in `retired/`. Their intent is re-expressed in maintained
island source and permanent tests, with the exact mapping in the registry.

`0009` remains because Rockchip's MPP userspace
hard-codes a `system-uncached` dma-heap name mainline does not provide, so
`mpph264enc` failed to register at all, and MPP performs no CPU cache
maintenance on a heap it believes is uncached, so cached memory under that name
encoded non-deterministically. `0009` registers a second heap under exactly
that name — non-cacheable mappings, a one-time cache clean at allocation, and
skipped CPU-sync only for that heap — reusing the `system_heap.c` extension
point `system_cc_shared` already has. Its board evidence was measured on v7.1.7
and is explicitly historical at the current v7.2 base.

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

The retired `0001` and `0005` plus active `0002` and `0003` are the work of **Ross Cawston**
([`rcawston`](https://github.com/rcawston)), ported from Rockchip's BSP MPP
driver, and are carried here byte-for-byte. This fork contributes packaging,
pinning, auditing, and CI.

`0009` is retained first-party CeraLive work. `0006` and `0008` remain archived
with their credit intact. The historical `0006`
is a device-tree change modelled on the Rockchip BSP's own
`hdmiin-sound` wiring (`rockchip,cpu = <&i2s7_8ch>`, receiver as clock master),
expressed with mainline's `simple-audio-card` instead of the BSP's `rockchip,hdmi`
machine driver. `0008` is a three-statement fix to the encoder driver `0001`
introduces, written against the pinned kernel's own DMA API. `0009` follows the
shape of the ACK/Rockchip uncached dma-heap, but is written against mainline's
`system_heap.c` and its existing per-heap drvdata mechanism rather than copied —
mainline has no `dma_heap_get_dev()`, so the one-time cache clean uses
`arch_dma_prep_coherent()`, the same primitive `dma_direct_alloc()` uses.

`0031`–`0039` are generated by CERALIVE/rk3588-media-island and copied here
byte-for-byte from its `v2026.9.2` release asset. The `Island(...)` variant and
independent verifier keep that provenance distinct from upstream commits,
first-party raw diffs, and unmerged lore postings.

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

`0042`–`0045` are Igor Paunovic's unmerged v4 HDMI-RX audio postings, imported
through that same canonical-mail pipeline. `0046`–`0049` are CeraLive deltas,
not edits to the upstream payload.
