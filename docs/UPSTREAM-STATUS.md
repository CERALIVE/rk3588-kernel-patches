# Upstream status and retire-on-merge tracking

**Base pin at last check:** `v7.1.7` — see [`kernel-pin.env`](../kernel-pin.env).
**Last full sweep:** 2026-08-08. **Rows added since:** `0009` (2026-08-09).
**Row-consistency re-check:** 2026-08-09 — every import and every evaluation from
this cycle has a row, and each row's verdict matches the series on disk. No
upstream status was re-resolved, so no **Last checked** date moved; a consistency
pass is not a sweep.
**Hardware validation update, 2026-08-09:** `0008` and `0009` moved from
`UNVALIDATED` to `VALIDATED` on Rock 5B+ following a real board session
(`image-building-pipeline` `.omo/evidence/image-pipeline-quality/hardware-validation-round1.md`);
Orange Pi 5+ remains `UNVALIDATED` — it has never run this image.

This repository carries out-of-tree patches. Every one of them is either waiting
for an upstream counterpart, tracking one, or has none and never will. This table
is the ledger of which is which, so that a kernel-base bump has a mechanical
answer to *"can this patch be dropped now?"* instead of a re-investigation.

It is a **status ledger, not a backlog**. A row that says "no upstream
counterpart" is a recorded fact, not a task; nothing here schedules work.

Related:
[`README.md`](../README.md) (what each patch does) ·
[`docs/REBASE-v7.1.7.md`](REBASE-v7.1.7.md) (does it still apply?) ·
[`docs/PROVENANCE.md`](PROVENANCE.md) (who wrote it, under what licence) ·
[`docs/BOARD-QUALIFICATION.md`](BOARD-QUALIFICATION.md) (what a real board has to
demonstrate before an `UNVALIDATED` marker may be cleared) ·
[`retired/REGISTRY.md`](../retired/REGISTRY.md) (what actually happens when a row's
retire trigger fires).

---

## Conventions

**Every lore reference is written `https://lore.kernel.org/r/<message-id>`.** That
form resolves a Message-ID against *every* archived list, so it keeps working when
a thread is cross-posted or when the list a patch was sent to is not the list you
guessed. Do not record a list-scoped `…/linux-rockchip/…` URL here — record the
Message-ID.

**Upstream-status vocabulary** (one token per row, and only these):

| Token | Meaning |
|---|---|
| `merged@<version>` | An upstream counterpart is merged and first appears in `<version>` |
| `sent-v<N>` | Posted to a kernel mailing list at revision `<N>`; **not** merged |
| `WIP` | Upstream work is known to exist but no mergeable series has been posted |
| `first-party-no-upstream` | CeraLive-authored, never submitted, no counterpart exists |
| `fork-carried-no-upstream` | Carried from the `rcawston` import; no Linux-mainline counterpart exists |

`merged@` and `sent-vN` describe the **upstream counterpart**, not our patch. A
`merged@7.2-rc1` row does *not* mean our patch is upstream — it means somebody
else's fix for the same problem is, which is exactly the condition a retire
trigger keys off.

**"Retire trigger" is a precondition, not an instruction.** When it fires, the
retirement itself still goes through the state machine in
[`retired/REGISTRY.md`](../retired/REGISTRY.md): the source file **moves** to
`retired/` byte-unchanged and gains a registry row. Nothing is ever `git rm`'d.

**"Last checked" is the date the row's upstream status was last re-verified
against a source**, not the date the patch was last touched.

---

## Current series members

The series has eight members. `0004` is a deliberate ordinal gap — upstream never
published one — and is not a row here for the same reason it is not a patch.

A row may carry an **`UNVALIDATED`** marker. That is a statement about *our* patch,
not about an upstream counterpart: it means the patch is source-correct and compiles
into a real kernel `.deb`, but the runtime behaviour it predicts has never been
observed on a board. It is orthogonal to the upstream-status token — a patch can be
`first-party-no-upstream` and validated, or unvalidated, independently. What clears
the marker for a given patch is written down, per patch, in
[`BOARD-QUALIFICATION.md`](BOARD-QUALIFICATION.md); nothing else clears it.

| Patch | Origin | Upstream status | Retire trigger | Last checked | Notes |
|---|---|---|---|---|---|
| `0001` vepu580 encoder (v3) | `upstream/` lane — imported from [`rcawston/rockchip-rk3588-mainline-patches`](https://github.com/rcawston/rockchip-rk3588-mainline-patches) @ `e13a311`; ported from the Rockchip BSP MPP driver. Upstream Linux counterpart: **N/A** | `WIP` — Collabora's rkvenc work, tracked at <https://lore.kernel.org/r/082e1141c38205222a91abf13b1a97d9a00e117a.camel@collabora.com> | **None foreseeable — track only.** Do *not* retire when rkvenc lands: see [§ 0001](#0001--do-not-retire-on-rkvenc-landing) | 2026-08-08 | Collabora table: VEPU580 H.264 = `WIP`, H.265 = `TODO` |
| `0002` hdmirx EDID fix (v1) | `upstream/` lane — Ross Cawston, same import. Upstream counterpart is `d1162a5adbb5` "media: synopsys: hdmirx: Fix HPD lane hold time", PATCHv2, <https://lore.kernel.org/r/20260325105742.63236-1-dmitry.osipenko@collabora.com> — **orthogonal work, already in our base** as `7dd27810eea0` | `merged@7.2-rc1` (the counterpart) — **and backported to the base at `v7.1.6`** | **None from this counterpart.** Retire only if the hardware-gated question below is answered "150 ms hold suffices"; base version is irrelevant to it | 2026-08-08 | **Upstream version rejected: nothing to adopt** — `7dd27810eea0` *is* the 7.2-rc1 fix (stable backport of `d1162a5adbb5`), it is already applied, and it is a 2-line HPD-hold change that shares no mechanism with `0002`. **4K60 input capability reviewed 2026-08-08: verdict unchanged and reinforced** — the driver's built-in EDID caps at 4K30 (`SCDC_Present = 0`), so 4K60 needs a runtime `S_EDID` write, which is the path `0002` fixes; 7 hardware-only checks (B1–B7) parked for T15. Verdict: [`EVAL-0002-EDID.md`](EVAL-0002-EDID.md). Read [§ 0002](#0002--one-upstream-answer-already-in-the-base) |
| `0003` hdmirx plugout fix (v1) | `upstream/` lane — Ross Cawston, same import. Upstream counterpart: **N/A** — none found (see [§ Sources](#sources-checked-for-this-sweep)) | `fork-carried-no-upstream` | None defined. Re-check at every base bump via the content check in [`REBASE-v7.1.7.md` § Patch-ID / content check](REBASE-v7.1.7.md#patch-id--content-check-against-the-new-base); retire only if a tree absorbs the `vb2_queue_error` plugout fix | 2026-08-08 | Content check at `v7.1.7`: `vb2_queue_error` still absent under `synopsys/hdmirx/` |
| `0005` hdmirx audio | `upstream/` lane — Ross Cawston, same import. Upstream counterpart is the 4-patch series **`[PATCH v4 0/4] media: synopsys: hdmirx: add HDMI audio capture support`** by Igor Paunovic, <https://lore.kernel.org/r/20260721064115.64809-1-royalnet026@gmail.com> — same mechanism, *competing* DT half | `sent-v4` — fully reviewed, **not merged**; author pinged for pickup 2026-08-05, unanswered | Counterpart merges **and** base reaches that version **and** Rock 5B+ enablement exists **and** the multichannel / jack / plugout regressions are closed. All four | 2026-08-08 | **Upstream version rejected: adoptable but not strictly better** — applies cleanly to `v7.1.7`, but drops multichannel, jack reporting, plugout teardown and pre-capture clock lock, and its 4/4 enables the card on **Orange Pi 5 Plus only**. Verdict: [`EVAL-0005-AUDIO.md`](EVAL-0005-AUDIO.md). Read [§ 0005 / 0006](#0005--0006--the-pairing-is-load-bearing-and-upstream-does-not-replace-it) |
| `0006` hdmirx audio sound card | `ceralive/` lane — **first-party CeraLive**. Never submitted (no `Signed-off-by`, deliberately — see [`PROVENANCE.md` §8](PROVENANCE.md#8-first-party-patches-ceralive)). Upstream counterpart: **partial only** — v4 3/4 covers the SoC-level card, v4 4/4 covers Orange Pi 5 Plus; **nothing upstream covers Rock 5B+** | `first-party-no-upstream` | Only if an upstream HDMI-RX audio series lands its own DT sound card **and** enables it on Rock 5B+ *and* Orange Pi 5+. As of 2026-08-08 the posted series does not | 2026-08-08 | **T11 answer: NOT superseded, and NOT compatible.** `0006` and v4 3/4 edit the same two regions of `rk3588-extra.dtsi` and disagree on `#sound-dai-cells` (`<0>` vs `<1>`); `git apply --check` of `0006` onto an upstream-applied tree fails. Modelled on the BSP's `hdmiin-sound` wiring, expressed with mainline `simple-audio-card`; no BSP text copied |
| `0007` iommu dte-limit fix | `backports/` lane — **backported from mainline** `8d4346ecd4950ae08cc76a6de327c264e846758c` "iommu/rockchip: disable fetch dte time limit", Simon Xue via Sven Püschel (Pengutronix), PATCHv2, <https://lore.kernel.org/r/20260428-spu-iommudtefix-v2-1-f592f579e508@pengutronix.de> | `merged@7.2-rc1` — `Acked-by` Heiko Stuebner, applied by Joerg Roedel 2026-06-02. **Absent from the base**: it carries no `Fixes:` tag and no `Cc: stable`, so `7.1.y` never picked it up | **Drop when base ≥ `v7.2`.** The base absorbing it is the whole retire condition — there is no merit question left, it is already mainline | 2026-08-08 | Sets `BIT(31)` of `MMU_AUTO_GATING` in `rk_iommu_enable()`, the vendor workaround for the RK356x/RK3588 blocked-VOP-and-black-screen and RK3588 RGA3 hang. Base check at `v7.1.7`: `DISABLE_FETCH_DTE_TIME_LIMIT` absent, `RK_MMU_AUTO_GATING` present. Applies forward with **no fuzz and no context adaptation**; **zero prerequisite commits**. Fixes:-tag sweep over mainline found **no follow-up** |
| `0008` rkvenc DMA max segment size — **`VALIDATED` on Rock 5B+ (2026-08-09), `UNVALIDATED` on Orange Pi 5+** | `ceralive/` lane — **first-party CeraLive**. Never submitted (no `Signed-off-by`, deliberately — see [`PROVENANCE.md` §8](PROVENANCE.md#8-first-party-patches-ceralive)). Fixes a bookkeeping defect in `0001`, so its upstream position is the `0001` row's. Upstream Linux counterpart: **N/A** | `first-party-no-upstream` — upstream rkvenc is `WIP` (Collabora's Mesa/Vulkan work, the same tracker as `0001`), and there is no upstream VEPU580 H.264 driver to backport a fix from | Only if `0001` itself retires, i.e. if an upstream VEPU580 driver ever replaces it wholesale. **Do not retire it on the strength of "upstream rkvenc landed"** — see [§ `0001`](#0001--do-not-retire-on-rkvenc-landing), which applies verbatim | 2026-08-09 | Adds `dma_set_max_seg_size(dev, DMA_BIT_MASK(32))` to `rkvenc_hw_probe()`, then **reads it back** with `dma_get_max_seg_size()` and fails the probe with `-EINVAL` if it did not take. Defect 2 of the 3 stacked in the pipeline's "MPP hardware video encode" KNOWN ISSUE. The IOVA guardrail in `rkvenc_service.c` is **deliberately untouched** — it correctly catches the symptom, and on a real board it never fired across 1080p, 4K, dual-core or a 10-minute soak. Read [§ `0008`](#0008--validated-on-rock-5b-and-what-that-does-and-does-not-mean). Hardware legs: [`BOARD-QUALIFICATION.md` §4](BOARD-QUALIFICATION.md) |
| `0009` `system-uncached` dma-heap — **`VALIDATED` on Rock 5B+ (2026-08-09), `UNVALIDATED` on Orange Pi 5+** | `ceralive/` lane — **first-party CeraLive**. Never submitted (no `Signed-off-by`, deliberately — see [`PROVENANCE.md` §8](PROVENANCE.md#8-first-party-patches-ceralive)). Ported in shape from the ACK/Rockchip uncached heap; no upstream Linux counterpart exists — mainline `drivers/dma-buf/heaps/` carries `system`, `system_cc_shared` and CMA only. Its reason to exist is the same `0001`/MPP stack, so its upstream position is the `0001` row's | `first-party-no-upstream` — upstream rkvenc is `WIP` (Collabora's Mesa/Vulkan work, the same tracker as `0001`), and no mainline series proposes an uncached system heap | Retire when **either** mainline registers an uncached system heap under exactly the name `system-uncached`, **or** `0001` retires wholesale, **or** the userspace stops hard-coding the name (a `librockchip-mpp` with a heap-name override or a working cached-heap fallback). Not before: the shipped `librockchip-mpp1 1.5.0-1` has neither | 2026-08-09 | Registers a second dma-heap from `system_heap.c` using the file's existing per-heap drvdata mechanism: `pgprot_writecombine()` mappings, a one-time `arch_dma_prep_coherent()` clean at allocation, and `DMA_ATTR_SKIP_CPU_SYNC` + skipped `dma_sync_sgtable_*` **only** for that heap. Defects **1 and 3** of the 3 stacked in the pipeline's "MPP hardware video encode" KNOWN ISSUE (`0008` is defect 2). Gated by its own `CONFIG_DMABUF_HEAPS_SYSTEM_UNCACHED`, which `depends on ARCH_HAS_DMA_PREP_COHERENT` so it cannot build where it would silently hand back cached memory. Confirmed a genuine second heap (minor `250,1`, not an alias of `system`'s `250,0`) that does not draw from CMA. Read [§ `0009`](#0009--validated-on-rock-5b-and-why-orange-pi-5-and-a-real-hdmi-source-stay-open) |

### `0001` — do not retire on rkvenc landing

The Collabora table's VEPU580 H.264 entry is `WIP`, and the linked thread says
Detlev Casanova and Daniel Almeida are building rkvenc around **Mesa and the
Vulkan Video API**, explicitly "quite different from existing V4L2 codec drivers".

`0001` is an MPP-service driver: `librockchip-mpp` drives it through
`include/uapi/linux/rkvenc.h`. A Vulkan-Video-based rkvenc is not a drop-in for
that uAPI, so "rkvenc merged" is **not** a sufficient condition to retire `0001`.
The condition that would matter is a mainline encoder that CeraLive's userspace
can actually drive — and that is a judgement about the whole engine stack, not a
version comparison. Hence: track only.

### `0002` — one upstream answer, already in the base

**The Collabora capture's "HDMI-RX EDID fix (7.2-rc1)" and the stable commit
`7dd27810eea0` in our base are the same fix in two trees, not two separate
efforts.** Evidence:

```
commit 7dd27810eea05554d9b43f74022bee9b37a86ac4   (first appears in v7.1.6)
    media: synopsys: hdmirx: Fix HPD lane hold time
    commit d1162a5adbb5e95953d460b5bde3a04cd4473fe9 upstream.
    Reported-by: Ross Cawston <ross@r-sc.ca>
    Closes: https://lore.kernel.org/r/20260209061654.54757-1-ross@r-sc.ca
```

The Collabora table's label names the *symptom* ("EDID fix"); the patch's own
subject is *"Fix HPD lane hold time"*. Message-ID
`20260325105742.63236-1-dmitry.osipenko@collabora.com` (patchwork id `14494411`,
project `linux-rockchip`) resolves to that same subject and to mainline
`d1162a5adbb5` (author date `2026-03-25T10:57:42Z` matches the posting to the
second; committed by Hans Verkuil 2026-05-05; contained in `v7.2-rc1`, not in
`v7.1`). `7dd27810eea0`'s own second line, `commit d1162a5adbb5… upstream.`,
confirms it is that same commit picked up via `Cc: stable`. It changes two lines
inside `hdmirx_hpd_ctrl()` — `msleep(100)` → `msleep(100 + 50)` — fixing the same
symptom `0002` exists for ("EDID change not detected by source/display side"),
reported by Ross Cawston (author of `0001`–`0005`) on 2026-02-09, the same date
`0002` carries.

**`0002` is unaffected by it.** `0002` only *adds call sites* to
`hdmirx_hpd_ctrl()` and rewires the EDID-write, signal-lock and DMA-reset paths;
it shares no line with the stable fix, which is net-zero lines and did not shift
a hunk offset. `0002` applies at `v7.1.7` with offsets only, and none of its own
symbols (`WAIT_SIGNAL_LOCK_TIME`, `NO_LOCK_CFG_RETRY_TIME`,
`WAIT_LOCK_STABLE_TIME`) exist in the base. The counterpart itself applies to
`v7.1.7` as a **no-op** (forward `git apply --check` fails, reverse succeeds,
`--3way` yields an empty diff), and it does not overlap `0002` — 2 lines of
HPD-hold duration versus `0002`'s 8 hunks of IRQ masking, lock-loop rework, phy
retry and DMA reset. **Verdict: KEEP `0002`.** Full write-up:
[`REBASE-v7.1.7.md` § Stable overlap](REBASE-v7.1.7.md#stable-overlap--7dd27810eea0-and-why-it-is-not-a-conflict)
and [`EVAL-0002-EDID.md`](EVAL-0002-EDID.md).

**Open, hardware-gated question — unresolved:**

> With `7dd27810eea0` in the base, is `0002`'s plugout/IRQ/HPD sequence still
> required for a source to re-read a written EDID, or is the +50 ms hold now
> sufficient on its own?

Answering it needs a real HDMI source and an RK3588 board; this repository gates
patch application only. Nothing here is board-verified. The standing bar
applies: the in-house `0002` "is already working very well", so the threshold
for replacing it is high, and nothing has come close to it.

**4K60 revisit, 2026-08-08 — verdict unchanged, held more firmly.** Both shipped
boards are specified for 4K@60 HDMI input. Decoding the driver's built-in
`edid_default[]` shows it advertises 2160p**30** at most (`Max_TMDS_Clock` `0x3C` =
300 MHz, HDMI-Forum `Max_TMDS_Character_Rate` = 0, **`SCDC_Present` = 0**, no
VIC 97), so 4K60 on these boards is reachable *only* by writing a custom EDID at
runtime — which is exactly the path `0002` repairs. `0002` is therefore a
functional prerequisite for 4K60, not merely a fix worth keeping. One proposed
argument did **not** survive checking and is recorded as corrected in the verdict
doc: EDID rides DDC/I²C, not TMDS, so the HPD-low hold constant is
resolution-independent. The hardware-gated question is re-stated against 4K60 as
item **B5** of the seven board checks parked for T15 in
[`EVAL-0002-EDID.md`](EVAL-0002-EDID.md) § Requires board validation at 4K60.

### `0005` / `0006` — the pairing is load-bearing, and upstream does not replace it

Read these two rows together or not at all. `0005` registers the ASoC codec;
`0006` is what turns that codec into an ALSA card. `image-building-pipeline`'s
own record of the diagnosis states it flatly:

> **HDMI-RX audio needs BOTH patch `0005` and patch `0006` — `0005` alone gives a
> bound codec and NO ALSA card.**

**Fact 1 — the base has nothing.** Content check across the whole
`drivers/media/platform/synopsys/hdmirx/` directory at `v7.1.7`:
`hdmirx_audio_startup`, `plugged_cb`, `HDMI_CODEC_DRV_NAME`, `sound/hdmi-codec.h`,
`AUDIO_ENABLE`, `SND_SOC_HDMI_CODEC`, `AUDIO_FIFO`, `snd_soc` — **0 hits each**.
There is no upstream HDMI-RX audio support in the base, in any form.

**Fact 2 — the upstream candidate applies, and is still declined.** All four
patches `git apply --check` clean on bare `v7.1.7` and on top of `0001`–`0003`,
and `git am` applies the whole series without conflict. Unlike `0002`'s
counterpart this one is genuinely importable. It is declined on merit:

- **Coverage regressions.** v4 has no channel-count detection (`hdmirx_audio_ch`,
  `AUDIO_PROC_CONFIG3`, `PKTDEC_AUDIF` — 0 hits), no jack/plug reporting
  (`hook_plugged_cb`, `plugged_cb`, `audio_present` — 0 hits), no audio teardown
  in `hdmirx_plugout()`, and starts its worker only at `hw_params()` so capture
  begins pre-lock. `0005` has all four.
- **Coverage gains, recorded fairly.** v4 handles system suspend (`0005` does
  not — its worker keeps polling gated clocks), sets `no_i2s_playback` /
  `no_spdif_playback` for a capture-only card, refuses S/PDIF with `-EOPNOTSUPP`,
  and carries an accepted DT binding.

**Fact 3 — the DT halves are competitors.** `0006` and v4 3/4 edit the same two
regions of `rk3588-extra.dtsi`, and disagree on the cell arity
(`#sound-dai-cells = <0>` + `sound-dai = <&hdmi_receiver>` versus `<1>` +
`<&hdmi_receiver 0>`). `git apply --check` of `0006` onto an upstream-applied tree
fails at `rk3588-extra.dtsi:338`. They cannot both be carried.

**Fact 4 — and this is the decider — upstream covers ONE of our two boards.**
v4 4/4 is titled *"enable HDMI RX audio capture on Orange Pi 5 Plus"* and enables
exactly that board. Measured on the adopted tree:

```
rk3588-rock-5b.dtsi              hdmi_receiver_sound:0  i2s7_8ch:0
rk3588-orangepi-5-plus.dts       hdmi_receiver_sound:1  i2s7_8ch:1
```

`ARMBIAN_BOARDS` is `rock-5b-plus orangepi5-plus`. Adopting the series as posted
would silently return Rock 5B+ to the bound-codec-no-card state, with no error
anywhere. `apply.sh`'s post-apply gate catches it —
`MISSING &i2s7_8ch in rk3588-rock-5b.dtsi` is a genuine failure, not a
label mismatch.

**Consequence — evaluated, and the answer is KEEP both.** `0006` is **not**
superseded: v4 3/4 supersedes its SoC-level half only, and nothing upstream
covers its Rock 5B+ half. Adoption would mean retiring `0006` and authoring a
replacement, not dropping it. Full verdict against all six criteria:
[`EVAL-0005-AUDIO.md`](EVAL-0005-AUDIO.md).

**What this does not resolve.** Nothing here is board-verified — no RK3588 board
is reachable from this repository. The advantages claimed for `0005` are read
from source, not demonstrated against a 5.1 source or a mid-stream cable pull.
Two `0005` defects are ledgered and left standing: no suspend handling, and
playback DAIs registered on a capture-only device. Neither has bitten a
device that never suspends.

### `0008` — `VALIDATED` on Rock 5B+, and what that does and does not mean

`0008` was the first series member to carry an explicit `UNVALIDATED` marker. A
real hardware validation session on 2026-08-09 cleared it **on Rock 5B+ only**
(`docs/BOARD-QUALIFICATION.md` §3–§4 ticked against transcripts; raw evidence in
image-building-pipeline's
`.omo/evidence/image-pipeline-quality/hardware-validation-round1.md`). Orange Pi
5+ has never run this image at all, so the marker stays `UNVALIDATED` on that
board specifically — this is a two-column result, not a fleet-wide one. It is
worth being precise about the claim, because the patch is unusually
well-grounded for something that took this long to confirm.

**What IS established.** The root cause was diagnosed on a real Rock 5B+ on
2026-08-02 and is recorded as defect 2 of 3 in the CeraLive
`image-building-pipeline` `AGENTS.md` KNOWN ISSUE *"MPP hardware video encode does
not work on the edge kernel"*. `rkvenc_dma_import_fd()` records an imported
dma-buf's length as `sg_dma_len(sgt->sgl)` — the first mapped segment, not the
mapping's total length — and `0001` never set a max segment size, so
`dma_get_max_seg_size()` answered its `SZ_64K` default and iommu-dma's
`__finalise_sg()` stopped coalescing there. The board reported a window of exactly
`0x10000` in every failing case, and the register it rejected was the source
frame's NV12 chroma-plane offset. The mechanism is checkable in the pinned tree:
`include/linux/dma-mapping.h` (`dma_get_max_seg_size()` → `SZ_64K`) and
`drivers/iommu/dma-iommu.c` `__finalise_sg()` (`max_len = dma_get_max_seg_size(dev)`,
then `max_len - cur_len >= s_length`).

**What IS now confirmed on a real board (Rock 5B+, 2026-08-09).** The IOVA
guardrail in `rkvenc_service.c` never fired across a real 1080p encode, 4K, a
dual-core two-session run, or an 18,000-frame/10-minute soak — while both
guardrail strings remained compiled into the shipped `rkvenc.ko`, so the silence
is a real negative rather than a removed check. `mpph264enc` registered
(`gst-inspect-1.0` exit 0) and a real 1080p/60-frame encode produced 1,854,524
bytes, byte-identical across 5 repeats, 3 resolutions, a reboot and 5.2 GiB of
memory pressure. This required `0008` **together with** `0009` — the fix
cannot be exercised on its own, since the KNOWN ISSUE names three stacked
defects and `0008` addresses only one of them (defect 2). `0009` is also now
`VALIDATED` on Rock 5B+; see its own section below.

**What is NOT established.** Orange Pi 5+ has never run this image, so nothing
above transfers to that board. Nor does anything above cover a real HDMI
capture source — the validation session encoded `videotestsrc` synthetic
frames only; no camera, no HDMI cable, and no second board were attached. A
full capture-to-encode-to-decode path with live video input remains untested
on either board.

**The check is on the EFFECT, not on a return value — because there is no return
value.** At `v7.1.7` `dma_set_max_seg_size()` is `static inline void`: it
`WARN_ON_ONCE()`s when `dev->dma_parms` is NULL and returns, leaving the `SZ_64K`
default in place. A `ret = dma_set_max_seg_size(...)` would not compile. The probe
therefore reads the value back with `dma_get_max_seg_size()` and fails with
`-EINVAL` on a mismatch, which is strictly stronger than a status check: the state
it refuses to boot into is exactly the defect being fixed. On the platform bus
`dma_parms` is always set (`drivers/base/platform.c` `setup_pdev_dma_masks()`), so
this is expected to pass on every `rkvenc` core; the check exists so a future base
that changes that fails loudly at probe instead of silently truncating every frame.

**The IOVA guardrail is deliberately untouched, and must stay that way.** The
guardrail in `rkvenc_service.c` rejects a translated register that falls outside
its buffer's mapped `[iova, iova+len)` window. With `len` truncated to 64 KiB the
chroma-plane offset genuinely IS outside that window, so the guardrail was right
every time it fired — it was reporting a bookkeeping bug one layer below it.
Silencing it would hide the defect and trade a clean `-EINVAL` for a DMA write past
the end of a mapping. `0008` touches exactly one file
(`drivers/media/platform/rockchip/rkvenc/rkvenc_hw.c`); `rkvenc_service.c` is
byte-unchanged.

**What cleared the marker on Rock 5B+.** A board with the series applied,
`mpph264enc` reachable, and the `guardrail: … outside iova` line absent from a
real encode — exactly [`BOARD-QUALIFICATION.md` §4](BOARD-QUALIFICATION.md)
(with §3 as the prerequisite), ticked against transcripts on 2026-08-09. **What
still clears it on Orange Pi 5+:** the same legs, on that board, which has
never booted this image. Until then, describe the edge-track encoder as
working on Rock 5B+ only — never as fleet-wide.

### `0009` — `VALIDATED` on Rock 5B+, and why Orange Pi 5+ and a real HDMI source stay open

`0009` was the second series member to carry an `UNVALIDATED` marker, and it was
the one where the marker mattered most: every other patch in this series can be
argued from source, this one could not. A real hardware validation session on
2026-08-09 cleared it **on Rock 5B+ only** — the same session and the same
scope caveat as `0008` above applies verbatim: Orange Pi 5+ has never run this
image, and no real HDMI capture source was attached.

**What IS established.** The two defects were diagnosed on a real Rock 5B+ on
2026-08-02 and recorded as defects 1 and 3 of 3 in the CeraLive
`image-building-pipeline` `AGENTS.md` KNOWN ISSUE. Defect 1:
`librockchip-mpp`'s dma-heap allocator table hard-codes `system-uncached` and has
no environment override, so with no such heap the H.264 HAL's init-time allocation
fails, `mpp_init(MPP_CTX_ENC, AVC)` fails, and the GStreamer plugin's registration
probe skips `mpph264enc` entirely — the board logged
`os_allocator_dma_heap_open open dma heap type 0 system-uncached failed!` followed
by `hal_h264e_vepu580_init init vepu buffer failed ret: -1`. Defect 3: MPP performs
no CPU cache maintenance on a heap it believes is uncached, so handed cached memory
it produced 231,047 then 161,997 bytes for byte-identical input and intermittent
CABAC decode failures. Both are measured facts, not inferences.

**What IS now confirmed on a real board (Rock 5B+, 2026-08-09).**
`/dev/dma_heap/system-uncached` exists as a genuine second heap — `crw-rw-rw-
root video 250,1` vs `system`'s `250,0`, with its own `/sys/class/dma_heap/`
entry — and it does **not** draw from CMA: holding a 1080p (3,110,400 B) and a
4K (12,441,600 B) allocation open simultaneously left `CmaFree` at 25,504 kB,
unchanged, while the identical pair from `default_cma_region` dropped it to
10,312 kB. Encoded output was byte-identical across 5 repeats, 3 resolutions,
a reboot and 5.2 GiB of memory pressure, and every stream decoded clean with
CABAC in use.

**What is NOT established: anything beyond Rock 5B+, and anything about a real
HDMI capture source.** Orange Pi 5+ has never run this image. The validation
run encoded synthetic `videotestsrc` frames only — no HDMI cable, no camera,
and no second board were attached — so the full capture-to-encode path with
real video input remains untested on both boards.

**The cache-alias subtlety is precisely why compile-only is not enough.** `0009`
makes the heap's own mappings non-cacheable — `pgprot_writecombine()` for `mmap()`
and for the internal `vmap()` — and cleans the pages to the point of coherency once
at allocation with `arch_dma_prep_coherent()`, because `__GFP_ZERO` zeroed them
through the cacheable linear map. What it does **not** do is tear down that linear
map alias. Those pages therefore keep a cacheable kernel alias for their whole
lifetime, and on arm64 a Normal-NC and a Normal-Cacheable alias of the same page are
architecturally permitted to lose coherency. The ACK/Rockchip heap this is ported
from has shipped with exactly that property at very large scale, which is evidence
and is not proof — and it is not evidence about this tree, this base or this board.

The consequence is what makes the proof mandatory rather than advisable: **getting
this subtly wrong does not produce an error.** It produces a frame that is slightly
wrong, sometimes. There is no return code, no `WARN`, no `dmesg` line and no
`-EINVAL` — which is the opposite of `0008`, whose failure mode is a probe that
refuses to bind. A compile proves the heap exists; only a board can prove the memory
behind it is coherent. The determinism and decode legs
([`BOARD-QUALIFICATION.md`](BOARD-QUALIFICATION.md) §5 and §6, plus the soak in §6d
and the pressure case in §6f) are the ones that can actually fail, and they are the
reason this document exists.

**What cleared the marker on Rock 5B+.** §2 through §7 of
[`BOARD-QUALIFICATION.md`](BOARD-QUALIFICATION.md), ticked against pasted
transcripts, on 2026-08-09 — 42 of the checklist's 65 items overall, covering
every leg reachable without a second board or a real HDMI source. **What
still clears it on Orange Pi 5+:** the same legs, on that board. **What still
clears it everywhere:** the items that stayed open regardless of board — a
real HDMI capture source (§8c/§8d/§8e, all seven of §9 B1–B7), a display
attached simultaneously with encode (§10a-3), and the combined
soak-plus-memory-pressure case noted as the next most valuable test. Nothing
less, and specifically not "it encoded a clip".

**What is deliberately not attempted, and must not be.** A
`/dev/dma_heap/system-uncached` symlink or `mknod` alias onto an existing heap. It
would make §2a and §3a pass and every later leg lie: aliasing the `system` heap
hands MPP cached memory it will not synchronise, and aliasing the CMA heap caps out
below 1080p (32 MiB pool fragmenting to a ~1.9 MiB largest run against a ~3.1 MiB
1080p NV12 frame). The pipeline's KNOWN ISSUE names it a corruption trap and used it
as a diagnostic instrument only.

### I2S MCLK gate clocks — skipped, known regression on Rock 5B+

The lore Message-ID this repository tracked is **v3**. The version that reached
mainline is **v4**, and it is five commits, not four — Heiko asked for the
`rockchip_clk_add_grf()` helper to be split out, so v4 3/5 exists only in the
merged form:

| v4 | mainline | file |
|---|---|---|
| 1/5 | `56c2ca0ae7cb` | `include/dt-bindings/clock/rockchip,rk3588-cru.h` |
| 2/5 | `28820fc7983b` | `drivers/clk/rockchip/clk.c` |
| 3/5 | `32d1d88c4165` | `drivers/clk/rockchip/clk.c` + `clk.h` |
| 4/5 | `06c990bffdbe` | `include/soc/rockchip/rk3588_grf.h` |
| 5/5 | `02b9b0bb6269` | `drivers/clk/rockchip/clk-rk3588.c` — **the payload** |

**Stop condition 1 — the prerequisite chain is four deep.** `02b9b0bb6269` alone
does not build on `v7.1.7`: it names `I2S0_8CH_MCLKOUT_TO_IO` (1/5),
`RK3588_SYSGRF_SOC_CON6` (4/5), `rockchip_clk_add_grf()` (3/5), and needs 2/5 for
the `grf_type_sys` branch to resolve through `aux_grf_table` at all. Content check
at `v7.1.7` — all four absent:

```
I2S0_8CH_MCLKOUT_TO_IO   0   (rockchip,rk3588-cru.h)
RK3588_SYSGRF_SOC_CON6   0   (rk3588_grf.h)
rockchip_clk_add_grf     0   (clk.c)
```

Every one of the five `git apply --check`s passes forward, so this is a
*build*-level chain, not a textual one — which is precisely why "it applies" was
not allowed to be the test. Four is over the two-commit ceiling, so the series is
recorded as **not cleanly backportable** rather than forced through.

**Stop condition 2 — the merged version regresses one of our two boards, and the
fix is not in mainline.** After the series landed, Diederik de Haas reported
(2026-06-23, in the v4 5/5 thread) that analog audio died on his NanoPC-T6 LTS.
Root cause, agreed by author and maintainer in-thread: the gates reset *open* and
firmware leaves them open, but once they became managed clocks with no consumer,
`clk_disable_unused()` closes them at boot. He confirmed it by reading `SOC_CON6`
at the U-Boot prompt (`md.l 0xfd58c318` → `0x600`, bit 0 clear = gate open) and
then by testing the proposed fix. Heiko's verdict: *"It is the correct fix, as it
returns the original way things worked for boards not activly handling that
clock."*

That fix — `CLK_IGNORE_UNUSED` on the four `_TO_IO` gates — was promised on
2026-06-24 and, as of 2026-08-08, **has not landed**: `clk-rk3588.c` has exactly
one commit since 2026-04-19, `02b9b0bb6269` itself. Importing today means
importing the known-buggy version with no follow-up available.

**And Rock 5B+ is in the blast radius, not adjacent to it.** The reporter's board
wires its codec to the *mux*, `clocks = <&cru I2S0_8CH_MCLKOUT>`, and no board in
the tree references `_TO_IO`. Rock 5B/5B+/5T is wired identically:

```
rk3588-rock-5b-5bp-5t.dtsi:396   es8316: audio-codec@11 {
                          :399           clocks = <&cru I2S0_8CH_MCLKOUT>;
rk3588-nanopc-t6.dtsi     :556           clocks = <&cru I2S0_8CH_MCLKOUT>;   <- the board that broke
```

So the import would trade an IOMMU-class bug we do not have for a silent loss of
headphone and mic audio on a board we ship. Re-open this row only when the
`CLK_IGNORE_UNUSED` follow-up is in mainline **and** the base is still below the
release that carries it.

---

## Import and evaluation candidates (T10–T13)

Seeded 2026-08-08 from the Collabora capture and the plan text. **These are
candidates, not commitments** — each row is filled in by the task that owns it,
and a documented *skip* is a valid outcome for every one of them.

**T13 imported none of its four.** That is the outcome, not a shortfall: all four
are *unmerged* postings, so unlike T12 there is no mainline SHA to resolve and no
`Fixes:` sweep to run — the questions are prerequisite depth and what the review
threads actually say. Three failed on depth (4, 6 and 3 against a ceiling of 2);
the fourth passed every mechanical test and was declined because its payload is a
userspace ABI whose key names upstream has already agreed to change. The series
is unchanged and `patches/` regenerates byte-identically.

| Candidate | Owning task | Origin | Upstream status | Retire trigger | Last checked | Notes |
|---|---|---|---|---|---|---|
| ~~HDMI-RX EDID fix (upstream counterpart to `0002`)~~ — **NOT IMPORTED** | T10 — **done** | <https://lore.kernel.org/r/20260325105742.63236-1-dmitry.osipenko@collabora.com> (PATCHv2) = mainline **`d1162a5adbb5e95953d460b5bde3a04cd4473fe9`** | `merged@7.2-rc1` — **and already in the base** as `7dd27810eea0` (`v7.1.6`) | n/a — nothing was imported | 2026-08-08 | **Upstream version rejected: already applied, and orthogonal.** It is the *same commit* as `7dd27810eea0`, not a second fix; it applies to `v7.1.7` as a no-op (reverse-apply check passes, `--3way` diff empty); and its 2-line HPD-hold change shares no mechanism with `0002`. `0002` is KEPT. Verdict: [`EVAL-0002-EDID.md`](EVAL-0002-EDID.md) |
| ~~HDMI Input Audio PATCHv4 (upstream counterpart to `0005`)~~ — **NOT IMPORTED** | T11 — **done** | <https://lore.kernel.org/r/20260721064115.64809-1-royalnet026@gmail.com> — `[PATCH v4 0/4] media: synopsys: hdmirx: add HDMI audio capture support`, Igor Paunovic, 4 patches | `sent-v4` — **not merged.** `Reviewed-by` Sebastian Reichel, Krzysztof Kozlowski and Dmitry Osipenko; `Tested-by` Dmitry on 2/4. Author pinged for media-tree pickup 2026-08-05, unanswered as of 2026-08-08 | n/a — nothing was imported | 2026-08-08 | **Upstream version rejected: adoptable, but not strictly better.** Applies clean to `v7.1.7` (all four, forward, no fuzz), so this is a merit rejection not a mechanical one. Drops multichannel, jack reporting, `hdmirx_plugout()` teardown and pre-capture clock lock; adds suspend support, capture-only DAI flags and an accepted binding. **`0006` answer: NOT superseded** — v4 4/4 enables the card on Orange Pi 5 Plus only, leaving Rock 5B+ with a bound codec and no ALSA card. Verdict: [`EVAL-0005-AUDIO.md`](EVAL-0005-AUDIO.md) |
| IOMMU "disable fetch dte time limit" — **IMPORTED as `0007`** | T12 — **done** | <https://lore.kernel.org/r/20260428-spu-iommudtefix-v2-1-f592f579e508@pengutronix.de> (PATCHv2) = mainline **`8d4346ecd4950ae08cc76a6de327c264e846758c`** | `merged@7.2-rc1` — **not in the base.** No `Fixes:` tag and no `Cc: stable`, so `7.1.y` will not pick it up on its own | **Drop when base ≥ `v7.2`** | 2026-08-08 | Now a series member — see the `0007` row in [§ Current series members](#current-series-members) |
| ~~I2S MCLK output gate clocks~~ — **NOT IMPORTED** | T12 — **done** | <https://lore.kernel.org/r/20260320-rk3588-mclk-gate-grf-v3-0-980338eacd2c@superkali.me> is **v3**; the version that merged is **v4**, <https://lore.kernel.org/r/20260419-rk3588-mclk-gate-grf-v4-0-513a42dd1dcc@superkali.me> — **5** commits: `56c2ca0ae7cb`, `28820fc7983b`, `32d1d88c4165`, `06c990bffdbe`, `02b9b0bb6269` | `merged@7.2-rc1` (all five; none in the base) | n/a — nothing was imported | 2026-08-08 | **Skipped on both stop conditions at once.** (1) **Prereq chain is 4 deep, over the 2-commit ceiling**: the payload `02b9b0bb6269` needs the clock IDs, the `grf_type_sys` lookup, `rockchip_clk_add_grf()` *and* the `SOC_CON6` offset, none of which `v7.1.7` has. (2) **The merged version is known-buggy and its fix has not landed** — see [§ MCLK](#i2s-mclk-gate-clocks--skipped-known-regression-on-rock-5b) |
| ~~V4L2 HW usage stats (fdinfo) for rkvdec + hantro~~ — **NOT IMPORTED** | T13 — **done** | <https://lore.kernel.org/r/20260617-v4l2-add-fdinfo-v2-0-d298e98ce06a@collabora.com> (PATCHv2) — 5 patches, Detlev Casanova + Christopher Healy | `sent-v2` — **not merged, and actively under revision.** **Zero** `Reviewed-by`/`Acked-by`/`Tested-by` on any of the five. Hans Verkuil, Mauro Carvalho Chehab and Nicolas Dufresne all filed change requests 2026-06-19; the author agreed to all of them on 2026-06-25. No v3 as of 2026-08-08 | n/a — nothing was imported. Row closes when merged upstream **and** base reaches that version | 2026-08-08 | **Skipped: the payload IS a userspace ABI, and upstream has already agreed to rename every key of it.** Mechanically it was the only one of T13's four that passed — `a01+a03+a04+a05` applies to bare `v7.1.7` with no fuzz and the chain is exactly **2 prerequisites**, *at* the ceiling. It is declined on merit — see [§ fdinfo](#v4l2-hw-usage-stats-fdinfo--skipped-the-key-names-are-already-agreed-to-change) |
| ~~V4L2 stateless codec tracepoints~~ — **NOT IMPORTED** | T13 — **done** | <https://lore.kernel.org/r/20260212162328.192217-1-detlev.casanova@collabora.com> (PATCHv1) — 11 patches, Detlev Casanova | `sent-v1` — **not merged, stalled.** No `Reviewed-by`/`Acked-by` anywhere. Steven Rostedt (tracing maintainer) filed a design objection on 01/11 on 2026-05-01; Nicolas Dufresne asked for filter granularity + documentation on 2026-04-28 and said of the fdinfo half *"I would hold on that until we have a bigger and robust plan"*. **No respin in the ~6 months since the posting**, and the fdinfo half was split out and re-sent as the row above | n/a — nothing was imported. Row closes when merged upstream **and** base reaches that version | 2026-08-08 | **Skipped on prerequisite depth (4, over the 2-commit ceiling) plus an unanswered maintainer objection.** The useful payload `09/11` needs `01/11` + `03/11` + `07/11` + `08/11`, and `03/11` does not even apply to bare `v7.1.7`. See [§ tracepoints](#v4l2-stateless-codec-tracepoints--skipped-four-deep-and-nakd-by-the-tracing-maintainer) |
| ~~PCIe System PM support~~ — **NOT IMPORTED** | T13 — **done** | <https://lore.kernel.org/r/20260316-rockchip-pcie-system-suspend-v5-0-5bb5ad37d643@collabora.com> (PATCHv5) — 8 patches (8/8 is `RFC`), Sebastian Reichel | `sent-v5` — **not merged.** No `Reviewed-by`/`Tested-by` on any patch. Shawn Lin (Rockchip PCIe) replied 2026-03-24 that the series *"doesn't cleanly apply to new -rc now so I assume it need a rebase"* **and** that patch 7 — the payload — *"actually put the host and device into D3cold unconditionly … which doesn't follow NVMe's requirement at least"*. No v6 as of 2026-08-08 | n/a — nothing was imported. Row closes when merged upstream **and** base reaches that version | 2026-08-08 | **Skipped on prerequisite depth (6, three times the ceiling) plus an unresolved correctness objection.** The payload `7/8` does not apply to `v7.1.7` even with `1/8`–`6/8` applied first — the series is based on `6de23f81a5e0` (v7.0-rc1). Rock 5B+ ships an M.2 NVMe slot, so the objection is on our hardware. See [§ PCIe PM](#pcie-system-pm--skipped-six-deep-and-the-payload-is-contested) |
| ~~SCDC link-health → connector debugfs~~ — **NOT IMPORTED** | T13 — **gated, evaluation done** | <https://lore.kernel.org/r/20260724-scdc-link-health-v9-0-bdda406d016d@collabora.com> (PATCHv9) — 5 patches, Nicolas Frattaroli | `sent-v9` — **not merged.** Best-reviewed of T13's four: `1/5` `Reviewed-by` Luca Ceresoli + Hans Verkuil, `3/5` `Reviewed-by` Maxime Ripard, `4/5` `Reviewed-by` Dmitry Baryshkov + `Acked-by` Maxime Ripard, `5/5` `Acked-by` Maxime Ripard. **`2/5` — the debugfs entry itself, i.e. the payload — carries no tag at all.** Jani Nikula's chardev question was resolved in-thread (*"Fair enough, thanks."*, 2026-07-28); `sashiko-bot`'s **1 [High] + 2 [Medium]** on `3/5` are **unanswered** | n/a — nothing was imported. Row closes when merged upstream **and** base reaches that version | 2026-08-08 | **Production-safety verdict: FAILS — but NOT for the reason the gate anticipated.** `debugfs` **IS mounted on the shipped image**, so "dead weight" does not apply. It fails on **relevance**: the series instruments DRM HDMI-**TX**, and CeraLive's HDMI concern is the V4L2 HDMI-**RX** capture driver it does not touch. Depth is **3**, over the ceiling. Full verdict: [§ SCDC](#scdc-link-health-debugfs--production-safety-verdict-fails-on-relevance-not-on-debugfs) |
| VDPU381 VP9 decode | tracked only — **do not import** | <https://lore.kernel.org/r/20260726-b4-add-rkvdec2-vp9-vdpu381-v1-0-180fb2d1f10c@gmail.com> (PATCHv1) | `sent-v1` — not merged | n/a — not carried | 2026-08-08 | Out of the chosen lane: a decode feature, not metrics/PM. Row exists so a future reader can see it was considered and excluded on purpose |
| VDPU381 multi-core (H.264/H.265) | tracked only — **do not import** | <https://lore.kernel.org/r/20260409-rkvdec-multicore-v1-0-62b316abf0f7@collabora.com> (PATCHv1) | `sent-v1` — not merged | n/a — not carried | 2026-08-08 | Same exclusion as the row above |

**Both first-party encoder patches have now landed**, and each is a row in
[§ Current series members](#current-series-members) rather than a candidate here:
`0008` (`dma_set_max_seg_size()` in the rkvenc probe) and `0009` (the
`system-uncached` dma-heap port). Both are `first-party-no-upstream`, and both are
now `VALIDATED` on Rock 5B+ (2026-08-09) / `UNVALIDATED` on Orange Pi 5+, and both
inherit their upstream position from the `0001` row (WIP rkvenc, tracked only).

The reservation this section used to carry about `0009` — that ARM cache-alias
handling done subtly wrong yields silent intermittent corruption in the video path
— was **not** withdrawn when the patch was written. It was converted into the
validation campaign it asked for:
[`BOARD-QUALIFICATION.md`](BOARD-QUALIFICATION.md) §2–§7, which a real Rock 5B+
session ticked 42 of the checklist's 65 items against transcripts on 2026-08-09
(reasoning: [§ `0009`](#0009--validated-on-rock-5b-and-why-orange-pi-5-and-a-real-hdmi-source-stay-open)).
Orange Pi 5+ and every leg requiring a real HDMI capture source stayed unticked —
the patch running on one board is not the whole campaign being closed.

### V4L2 HW usage stats (fdinfo) — skipped, the key names are already agreed to change

**This one passed every mechanical test, and that is why the skip has to be
argued rather than asserted.** Recorded as a PASS so nobody re-runs a 2 GB clone
to rediscover it:

| Check | Result at `v7.1.7` |
|---|---|
| `git apply --check` forward, `1/5` `3/5` `4/5` `5/5` | PASS each; reverse FAIL each (⇒ absent from base) |
| Stacked `a01 → a03 → a04 → a05` on bare `v7.1.7` | **applies, no fuzz, no context adaptation** |
| Prerequisite depth for either driver patch | **2** — `1/5` (the `show_fdinfo` fop) and `3/5` (the `v4l2_stats` interface). *At* the ceiling, not over |
| Symbol probe of the base | `show_fdinfo` 0 · `v4l2_show_fdinfo` 0 · `v4l2-stats.c` absent · `v4l2-stats.h` absent · `MEDIA_DEV_TYPE_*` 0 · `fh->stats` 0 · `ktime_t start_time` 0 in both driver ctxs |
| Target drivers present in base | `drivers/media/platform/rockchip/rkvdec` **and** `drivers/media/platform/verisilicon` both present |

**The disqualifying fact is what the patch set actually is.** `4/5` and `5/5` do
not add a debug print — they publish a **key namespace in
`/proc/<pid>/fdinfo/<fd>`**, which is userspace ABI. `2/5` documents exactly five
keys:

```
media-driver:           hantro-vpu
media-type:             decoder
media-engine-usage:     123456789 ns
media-maxfreq:          600000000 Hz
media-curfreq:          600000000 Hz
```

**All five are already agreed to be renamed**, in-thread, by the author. Hans
Verkuil, 2026-06-19: the `media-` prefix *"is too generic … it also looks like it
refers to the /dev/mediaX device"*, `media-engine` is *"Very vague"*,
`media-type` is a *"Poor name"*, and on `3/5` — *"Poor name, and it conflicts
with ISP statistics. How about `v4l2_pdinfo`? And `v4l2-fdinfo.h` etc."* plus
*"I'm a bit unhappy about introducing yet another type. Do we need it?"*. Mauro
Carvalho Chehab, same day: a `Documentation/ABI/testing/` entry is required
*"on your next spin"*. The author's reply on 2026-06-25 accepts all of it —
`v4l2-driver`, `v4l2-driver-type`, `v4l2-core-usage-time-<core_id>`,
`v4l2-maxfreq-<core_id>`, the struct renamed to *"metrics"*, and the doc
restructured into generic-plus-per-type sections.

So importing today means shipping an fdinfo key set that upstream has already
decided is wrong. When v3 lands we would have to break our own userspace, and
the whole point of the row's retire trigger — base absorbs it, we drop the patch
— stops working, because the absorbed version would not be what we shipped.

**Second, weaker reason, recorded because it bears on the value side.** The
series instruments **decoders**: `rkvdec` and `hantro`. CeraLive's data flow is
capture → **encode** → bond → stream, and none of the 29 patches read for T13
touches `rkvenc`/VEPU580 — the engine `0001` exists for. The observability this
would buy on a shipped board today is close to zero.

Re-open when a revision lands with the renamed keys and a
`Documentation/ABI/testing/` entry, or sooner if an rkvenc fdinfo implementation
appears.

### V4L2 stateless codec tracepoints — skipped, four deep and NAK'd by the tracing maintainer

**Stop condition 1 — the prerequisite chain is four.** The payload for this
repository is `09/11` (*"media: hantro: Add v4l2_hw run/done traces"*). It needs:

| Needed by the payload | Supplied by | In `v7.1.7`? |
|---|---|---|
| `trace_v4l2_hw_run` / `trace_v4l2_hw_done` | `08/11` | no — 0 hits in `include/trace/events/v4l2.h` |
| `v4l2_stream_class` (the class `08/11` extends) | `07/11` | no — 0 hits |
| `ctx->fh.tgid` / `ctx->fh.fd` | `03/11` | no — no `tgid` or `fd` in `include/media/v4l2-fh.h` |
| the `v4l2-trace.c` context `08/11` patches into | `01/11` | no — `v4l2_ctrl_av1_sequence` 0 hits; `include/trace/events/v4l2_requests.h` absent; visl still owns all nine of its `visl-trace-*` headers |

Four, over the two-commit ceiling. And unlike the MCLK case this is not even a
build-only chain: `02/11`, `03/11`, `04/11`, `06/11` and `08/11` all **fail**
`git apply --check` on bare `v7.1.7`, and the stacked attempt stops at `03/11`.
`01/11` alone is a 1,645-line move of the visl trace headers into
`include/trace/events/`.

**Stop condition 2 — an unanswered design objection from the tracing
maintainer.** Steven Rostedt, 2026-05-01, on `01/11`:

> *"What the heck! You are copying an entire structure onto the ring buffer to
> print just a portion of it? This is really a waste of ring buffer, and also
> prevents you from doing any real filtering."*

…with a worked example of field-based filtering and pointers to `libtracefs` /
`libtraceevent`. Nicolas Dufresne (2026-04-28) is broadly positive — *"I like the
direction"* — but asks for filter granularity and documentation, and on `11/11`
says of the fdinfo half *"I think overall that this fdinfo implementation is a bit
limited … I would hold on that until we have a bigger and robust plan."* Nothing
in the thread answers Rostedt, there is **no `Reviewed-by` or `Acked-by`
anywhere**, and no revision has been posted since 2026-02-12.

**And it is partly superseded already.** `10/11` and `11/11` are the fdinfo half;
they were split out and re-sent as the `v2` series in the row above. So this
posting is the *tracing* half only, stalled on a maintainer objection about ring
buffer usage that would have to be rewritten before it lands.

### PCIe System PM — skipped, six deep and the payload is contested

**Stop condition 1 — six prerequisites.** The payload is `7/8`
(*"PCI: dw-rockchip: Add system PM support"*); `1/8` through `6/8` are the
regulator restore, the `devm_phy_get` move and the four helper extractions it is
written against. Content probe of `drivers/pci/controller/dwc/pcie-dw-rockchip.c`
at `v7.1.7` — every helper the payload calls is absent:

```
rockchip_pcie_get_ltssm_status_reg  0     rockchip_pcie_get_ltssm_state  0
rockchip_pcie_set_mode              0     rockchip_pcie_enable_ltssm_ctrl 0
rockchip_pcie_suspend               0     rockchip_pcie_resume            0
pme_turn_off                        0
rockchip_pcie_get_ltssm             6     (the OLD name, pre-1/8..5/8)
```

The DWC core half *is* there — `dw_pcie_suspend_noirq` /
`dw_pcie_resume_noirq` exist in `pcie-designware-host.c` — so the gap is entirely
the Rockchip glue. Six is three times the ceiling.

**Stop condition 2 — it does not apply, and upstream said so first.** `7/8` fails
`git apply --check` on bare `v7.1.7` *and* fails after `1/8`–`6/8` are applied in
order. The series declares `base-commit: 6de23f81a5e08be8fbf5e8d7e9febc72a5b5f27f`
(a v7.0-rc1 rebase), and Shawn Lin already recorded the same thing on-list on
2026-03-24: *"It doesn't cleanly apply to new -rc now so I assume it need a
rebase."*

**Stop condition 3 — the payload has an unresolved correctness objection, on our
hardware.** Same message, from the Rockchip PCIe maintainer:

> *"I think patch 7 actually put the host and device into D3cold unconditionly,
> with reset the controller，power-off 3v3 and deassert perst# which doesn't
> follow NVMe's requirement at least. Krishna is working on it [1], it would be
> better to follow the same patten."*

Rock 5B+ ships an M.2 NVMe slot, so "doesn't follow NVMe's requirement" is not a
distant concern. `8/8` is explicitly `RFC` and its own author writes *"I'm not
sure about the rationale"*; the only substantive reply to it is Shawn Lin
confirming the register write is *"not strictly necessary from a functional
standpoint"*. No patch in the series carries a `Reviewed-by` or `Tested-by`, and
no v6 exists as of 2026-08-08.

Re-open at v6-or-later, once the D3cold sequence follows whatever pattern the
referenced `d3cold` series settles on.

### SCDC link-health debugfs — production-safety verdict: FAILS on relevance, not on debugfs

This row was **gated** on a production-safety evaluation, and the brief required
the verdict be recorded either way. It is recorded here in full, including the
part that came out the *opposite* way to the gate's own hypothesis.

**Safety question 1 — is `debugfs` even mounted on the shipped image? YES.** The
gate anticipated that it might not be, in which case the patch would be dead
weight. It is mounted, on both counts:

```
image-building-pipeline/v2/mkosi/build/base/usr/lib/systemd/system/
    sys-kernel-debug.mount                       Type=debugfs  Where=/sys/kernel/debug
    sysinit.target.wants/sys-kernel-debug.mount  <- pulled into sysinit.target
```

…and it survives the image's own unit policy: `suppress_unusable_boot_units` in
`v2/mkosi/customize/postinst.d/services.sh` masks exactly six units
(`systemd-networkd.service`/`.socket`/`-wait-online.service`,
`systemd-machine-id-commit.service`, `dnsmasq.service`, `chrony-wait.service`) and
this is not one of them. Corroborated on real hardware: the pipeline's own
`AGENTS.md` records reading `/sys/kernel/debug/usb/tcpm-4-0022/log` on a live
Rock 5B+ while root-causing the Type-C role race. **So the file would be created
and readable — this is a live interface, not an inert one.** Exposure is bounded
to root by the kernel's own `0700` on `/sys/kernel/debug`, and the mount is
`nosuid,nodev,noexec`.

**Safety question 2 — Kconfig dependencies.** `drm_scdc_helper.c` is built under
the DRM display-helper Kconfig, and `2/5` adds `#include <linux/debugfs.h>` +
`debugfs_create_file()` with **no `CONFIG_DEBUG_FS` guard**. That is legal — the
stubs return `ERR_PTR(-ENODEV)` — so there is no build break with `DEBUG_FS=n`,
but the parsing code and its 256-byte state buffer compile unconditionally. Every
symbol it needs does exist in the base: `wrapping_add` (`include/linux/overflow.h`),
`kzalloc_obj` (`include/linux/slab.h`), and the whole `SCDC_ERR_DET_*` /
`SCDC_CHANNEL_VALID` register set (`include/drm/display/drm_scdc.h`).

**Safety question 3 — runtime overhead.** `scdc_status_show()` takes
`connector->dev->mode_config.mutex` — the global DRM modeset lock — and then
performs **two 128-byte I²C DDC reads** per open. The cover letter's stated usage
is *"To continually poll the link status, userspace can poll the debugfs file."*
On a device whose job is an uninterrupted live stream, a polling reader would
serialise against modeset on that lock and put sustained traffic on the same DDC
bus the display driver uses. Not fatal, but this is a bring-up instrument, not a
metric to poll.

**Safety question 4 — and this is the one that decides it — relevance. The series
instruments the wrong HDMI direction for this product.** It is DRM HDMI-**TX**
only: `drm_scdc_helper.c`, `drm_hdmi_state_helper.c`, `drm_bridge_connector.c`,
with fixups for sun4i and vc4. On RK3588 the only consumer is `dw_hdmi_qp` — the
HDMI **output** — confirmed as the sole `drm_hdmi_connector*` user across
`drivers/gpu/drm/bridge/synopsys/` and `drivers/gpu/drm/rockchip/`. CeraLive's
HDMI concern is HDMI-**RX** capture, which is
`drivers/media/platform/synopsys/hdmirx/snps_hdmirx.c` — a **V4L2** driver with
its own register-level SCDC block (`hdmirx_scdc_init`, `SCDC_CONFIG`,
`SCDC_REGBANK_CONFIG0`) that this series does not touch. The SCDC facts T10
identified as the 4K60 gate — `SCDC_Present`, the 1/40 TMDS bit-clock ratio — are
on the **RX** side. The file would appear on the local-monitor connector and tell
an operator nothing about the capture link.

**Depth — 3, over the ceiling.** For `scdc_status` to *exist* on a connector, the
minimal set is `1/5` + `2/5` + `4/5` + `5/5`: `2/5` does not apply to bare
`v7.1.7` (it needs `1/5`'s `ssize_t`→`int` context), `drm_hdmi_connector_debugfs_init`
does not exist in the base so `5/5` hard-depends on `4/5`, and without `4/5`+`5/5`
nothing ever calls `drm_scdc_debugfs_init` — the file is never created. The
stacked attempt stops at `4/5`, which is a 162-insert/157-delete cross-driver
refactor moving the HDMI infoframe debugfs machinery out of `drm_debugfs.c` (6
matches present in the base) and fixing up two drivers we do not ship.

**Review status, recorded fairly — this is the best-reviewed of T13's four.**
`1/5` `Reviewed-by` Luca Ceresoli + Hans Verkuil; `3/5` `Reviewed-by` Maxime
Ripard; `4/5` `Reviewed-by` Dmitry Baryshkov + `Acked-by` Maxime Ripard; `5/5`
`Acked-by` Maxime Ripard. Jani Nikula asked why not a chardev like
`DRM_DISPLAY_DP_AUX_CHARDEV` and accepted the answer (*"Fair enough, thanks."*,
2026-07-28). Two things still stand: **`2/5` — the payload — has no review tag at
all**, and `sashiko-bot`'s 2026-07-24 findings on `3/5` are **unanswered in the
thread**, including a `[High]` that v9's own change to include the Lane 3
registers in the zero-sum check breaks SCDC reads on 4-lane FRL *exactly when
errors are present* — i.e. in the one condition the feature exists to observe.

**Verdict: skipped.** Not because debugfs is absent — it is present — but because
it instruments HDMI-TX on a device whose HDMI question is RX, at a depth of three
including a refactor of two unrelated drivers, with an unanswered `[High]` on the
FRL patch. Re-open only if an equivalent lands for `snps_hdmirx`, or if the DRM
HDMI-TX link ever becomes something this product diagnoses.

---

## Honest gaps

**As of 2026-08-08, in the Collabora mainline-status table and the lore threads it
links** (that qualifier is the whole point of this section — it is a statement
about two named sources on one named date, not a universal negative about the
kernel):

- **No RK3588 Bluetooth backport candidates found.** The Collabora table carries
  no Bluetooth row at all, and no linked thread in either the pending or merged
  improvements list concerns RK3588 Bluetooth. This is consistent with the shipped
  boards, where Bluetooth is **USB-side and handled in userspace** — so there is
  nothing for a kernel-patch repository to carry here regardless.
- **GPU (panthor), DFI and thermal-ADC metrics are already in `v7.1.y`.** The
  capture shows GPU `6.10-rc1`, DFI `6.7-rc1` ("DDR memory utilization for perf"),
  Thermal ADC `6.4-rc1`, plain ADC `6.5-rc1` — all well below the pinned base, so
  there is nothing to backport.
- **DMC and deeper power telemetry are upstream-TODO — nothing importable.** The
  capture lists DMC (Dynamic Memory Controller, memory frequency scaling) as
  `TODO` with no linked series. There is no posting to backport; this is an
  absence upstream, not a gap in this repository.

None of the three is a work item, and none should be turned into one. They are
recorded so the next person does not repeat the search and reach the same three
dead ends.

### Sources checked for this sweep

| Source | How | Snapshot |
|---|---|---|
| Collabora `mainline-status.md` | Fetched 2026-08-08 with a real browser (Playwright 1.61.1 / Chromium) — the page sits behind an Anubis proof-of-work gate that a plain `curl` cannot pass | `.omo/evidence/image-pipeline-quality/collabora-mainline-status-2026-08-08.md` (untracked; `.omo/` is gitignored) — sha256 `729b87afb5a4fb097713b79e264a3688e25f3f971a8b9fcbc6c73d49340dccb9` |
| Every lore thread linked from the rows above | `https://lore.kernel.org/r/<message-id>` resolution check, 2026-08-08 | All 12 Message-IDs resolved (HTTP 302 to `/all/…`); zero 404s |
| The `0005` counterpart thread, **read in full** | `https://lore.kernel.org/all/<message-id>/t.mbox.gz` — the gzipped thread mbox is served to plain `curl`, unlike the HTML views and `/raw` (both 403). `patchwork.kernel.org`'s API returns **zero** results for this Message-ID, so T10's patchwork route does not work here | 34 messages, 4 patches, 3 human reviewers + `sashiko-bot`; every `Reviewed-by`/`Tested-by` quoted in [`EVAL-0005-AUDIO.md`](EVAL-0005-AUDIO.md) |
| The pinned kernel tree at `v7.1.7` | Path + content checks per patch | [`REBASE-v7.1.7.md` § Patch-ID / content check](REBASE-v7.1.7.md#patch-id--content-check-against-the-new-base) — 0 of 5 absorbed |
| Both T12 import-candidate threads, **read in full** | Same `t.mbox.gz` route as the `0005` row. `lore.kernel.org`'s *search* endpoint (`/all/?q=…&x=m`) is **also 403** — only a thread fetched by a known Message-ID is served, so a "Fixes: sweep" cannot be run against lore | IOMMU: 3 messages (`Acked-by` Heiko, "Applied, thanks" from Joerg). MCLK: the v3 thread is 9 messages, and the **v4** thread it became is 18, including the post-merge regression report |
| All four T13 candidate threads, **read in full** | Same `t.mbox.gz` route, one fetch per Message-ID, all HTTP 200 to plain `curl`. Every reply body read, not just the patches — which is where three of the four verdicts came from | fdinfo 12 unique msgs (24 raw) · tracepoints 22 (44) · PCIe PM 11 (22) · SCDC 10 (10). **Zero** `Reviewed-by`/`Acked-by`/`Tested-by` across the first three; five review tags across SCDC, none of them on its payload patch |
| Applicability + symbol existence for all 29 T13 patches | `git apply --check` forward **and** reverse per patch against a clean `v7.1.7` worktree, then a stacked `git apply` of each candidate's minimal useful set, then an identifier probe of the base for every symbol the payloads name (per T12's "applies ≠ compiles" rule) | 12 of 29 fail even a textual forward apply. Minimal stacks: fdinfo **applies**; tracepoints stops at `03/11`; PCIe PM stops at `7/8`; SCDC stops at `4/5` |
| Is `debugfs` mounted on the shipped image? (the SCDC gate) | Direct inspection of `image-building-pipeline/v2/mkosi` — the built base layer's systemd unit tree and the image's own unit-masking policy — plus the pipeline's real-hardware notes | **Yes.** `sys-kernel-debug.mount` present *and* in `sysinit.target.wants/`; not among the six units `suppress_unusable_boot_units` masks; `/sys/kernel/debug/...` demonstrably read on a live Rock 5B+ |
| Mainline commit resolution and the **`Fixes:` sweep** | `api.github.com/search/commits` over `torvalds/linux` for identity (author date matched to the posting, to the second), `…/compare/<sha>…v7.2-rc1` for containment (`status: ahead`, `behind_by: 0`), then `…/commits?path=<file>&since=<merge-date>` per touched file — a bounded per-file sweep, which is what makes "no follow-up exists" a measured claim rather than an absent search hit | 6 SHAs resolved, all contained in `v7.2-rc1`. Sweep over all five touched files: **zero** commits carrying a `Fixes:` tag naming any of them; the only extra commit surfaced was `32d1d88c4165`, which is a *prerequisite* of the MCLK series, not a fix to it |

**The Collabora capture is a snapshot, not a live feed.** Re-capture it — with a
browser, not `curl` — at every base bump, and move the "Last checked" dates in the
same change. A stale date is the honest signal that a row has not been re-verified.

---

## Updating a row

1. Re-capture the Collabora table (browser required) and re-resolve the row's
   Message-ID.
2. Update **Upstream status** and **Last checked** together. A status change with
   an unchanged date is not a check.
3. If the retire trigger has fired, do the retirement through
   [`retired/REGISTRY.md`](../retired/REGISTRY.md) — **move** the source file, add
   the registry row, drop the `SERIES` entry, regenerate `patches/`. Then point
   this row's Notes at the registry entry.
4. If an import lands, replace the candidate row's placeholder provenance with the
   real `commit <sha> upstream.` value recorded in the `backports/` header.
