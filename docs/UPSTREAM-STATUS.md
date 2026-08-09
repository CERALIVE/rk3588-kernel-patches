# Upstream status and retire-on-merge tracking

**Base pin at last check:** `v7.1.7` — see [`kernel-pin.env`](../kernel-pin.env).
**Last full sweep:** 2026-08-08.

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

The series has seven members. `0004` is a deliberate ordinal gap — upstream never
published one — and is not a row here for the same reason it is not a patch.

A row may carry an **`UNVALIDATED`** marker. That is a statement about *our* patch,
not about an upstream counterpart: it means the patch is source-correct and compiles
into a real kernel `.deb`, but the runtime behaviour it predicts has never been
observed on a board. It is orthogonal to the upstream-status token — a patch can be
`first-party-no-upstream` and validated, or unvalidated, independently.

| Patch | Origin | Upstream status | Retire trigger | Last checked | Notes |
|---|---|---|---|---|---|
| `0001` vepu580 encoder (v3) | `upstream/` lane — imported from [`rcawston/rockchip-rk3588-mainline-patches`](https://github.com/rcawston/rockchip-rk3588-mainline-patches) @ `e13a311`; ported from the Rockchip BSP MPP driver. Upstream Linux counterpart: **N/A** | `WIP` — Collabora's rkvenc work, tracked at <https://lore.kernel.org/r/082e1141c38205222a91abf13b1a97d9a00e117a.camel@collabora.com> | **None foreseeable — track only.** Do *not* retire when rkvenc lands: see [§ 0001](#0001--do-not-retire-on-rkvenc-landing) | 2026-08-08 | Collabora table: VEPU580 H.264 = `WIP`, H.265 = `TODO` |
| `0002` hdmirx EDID fix (v1) | `upstream/` lane — Ross Cawston, same import. Upstream counterpart is `d1162a5adbb5` "media: synopsys: hdmirx: Fix HPD lane hold time", PATCHv2, <https://lore.kernel.org/r/20260325105742.63236-1-dmitry.osipenko@collabora.com> — **orthogonal work, already in our base** as `7dd27810eea0` | `merged@7.2-rc1` (the counterpart) — **and backported to the base at `v7.1.6`** | **None from this counterpart.** Retire only if the hardware-gated question below is answered "150 ms hold suffices"; base version is irrelevant to it | 2026-08-08 | **Upstream version rejected: nothing to adopt** — `7dd27810eea0` *is* the 7.2-rc1 fix (stable backport of `d1162a5adbb5`), it is already applied, and it is a 2-line HPD-hold change that shares no mechanism with `0002`. **4K60 input capability reviewed 2026-08-08: verdict unchanged and reinforced** — the driver's built-in EDID caps at 4K30 (`SCDC_Present = 0`), so 4K60 needs a runtime `S_EDID` write, which is the path `0002` fixes; 7 hardware-only checks (B1–B7) parked for T15. Verdict: [`EVAL-0002-EDID.md`](EVAL-0002-EDID.md). Read [§ 0002](#0002--one-upstream-answer-already-in-the-base) |
| `0003` hdmirx plugout fix (v1) | `upstream/` lane — Ross Cawston, same import. Upstream counterpart: **N/A** — none found (see [§ Sources](#sources-checked-for-this-sweep)) | `fork-carried-no-upstream` | None defined. Re-check at every base bump via the content check in [`REBASE-v7.1.7.md` § Patch-ID / content check](REBASE-v7.1.7.md#patch-id--content-check-against-the-new-base); retire only if a tree absorbs the `vb2_queue_error` plugout fix | 2026-08-08 | Content check at `v7.1.7`: `vb2_queue_error` still absent under `synopsys/hdmirx/` |
| `0005` hdmirx audio | `upstream/` lane — Ross Cawston, same import. Upstream counterpart is the 4-patch series **`[PATCH v4 0/4] media: synopsys: hdmirx: add HDMI audio capture support`** by Igor Paunovic, <https://lore.kernel.org/r/20260721064115.64809-1-royalnet026@gmail.com> — same mechanism, *competing* DT half | `sent-v4` — fully reviewed, **not merged**; author pinged for pickup 2026-08-05, unanswered | Counterpart merges **and** base reaches that version **and** Rock 5B+ enablement exists **and** the multichannel / jack / plugout regressions are closed. All four | 2026-08-08 | **Upstream version rejected: adoptable but not strictly better** — applies cleanly to `v7.1.7`, but drops multichannel, jack reporting, plugout teardown and pre-capture clock lock, and its 4/4 enables the card on **Orange Pi 5 Plus only**. Verdict: [`EVAL-0005-AUDIO.md`](EVAL-0005-AUDIO.md). Read [§ 0005 / 0006](#0005--0006--the-pairing-is-load-bearing-and-upstream-does-not-replace-it) |
| `0006` hdmirx audio sound card | `ceralive/` lane — **first-party CeraLive**. Never submitted (no `Signed-off-by`, deliberately — see [`PROVENANCE.md` §8](PROVENANCE.md#8-first-party-patches-ceralive)). Upstream counterpart: **partial only** — v4 3/4 covers the SoC-level card, v4 4/4 covers Orange Pi 5 Plus; **nothing upstream covers Rock 5B+** | `first-party-no-upstream` | Only if an upstream HDMI-RX audio series lands its own DT sound card **and** enables it on Rock 5B+ *and* Orange Pi 5+. As of 2026-08-08 the posted series does not | 2026-08-08 | **T11 answer: NOT superseded, and NOT compatible.** `0006` and v4 3/4 edit the same two regions of `rk3588-extra.dtsi` and disagree on `#sound-dai-cells` (`<0>` vs `<1>`); `git apply --check` of `0006` onto an upstream-applied tree fails. Modelled on the BSP's `hdmiin-sound` wiring, expressed with mainline `simple-audio-card`; no BSP text copied |
| `0007` iommu dte-limit fix | `backports/` lane — **backported from mainline** `8d4346ecd4950ae08cc76a6de327c264e846758c` "iommu/rockchip: disable fetch dte time limit", Simon Xue via Sven Püschel (Pengutronix), PATCHv2, <https://lore.kernel.org/r/20260428-spu-iommudtefix-v2-1-f592f579e508@pengutronix.de> | `merged@7.2-rc1` — `Acked-by` Heiko Stuebner, applied by Joerg Roedel 2026-06-02. **Absent from the base**: it carries no `Fixes:` tag and no `Cc: stable`, so `7.1.y` never picked it up | **Drop when base ≥ `v7.2`.** The base absorbing it is the whole retire condition — there is no merit question left, it is already mainline | 2026-08-08 | Sets `BIT(31)` of `MMU_AUTO_GATING` in `rk_iommu_enable()`, the vendor workaround for the RK356x/RK3588 blocked-VOP-and-black-screen and RK3588 RGA3 hang. Base check at `v7.1.7`: `DISABLE_FETCH_DTE_TIME_LIMIT` absent, `RK_MMU_AUTO_GATING` present. Applies forward with **no fuzz and no context adaptation**; **zero prerequisite commits**. Fixes:-tag sweep over mainline found **no follow-up** |
| `0008` rkvenc DMA max segment size — **`UNVALIDATED` on hardware** | `ceralive/` lane — **first-party CeraLive**. Never submitted (no `Signed-off-by`, deliberately — see [`PROVENANCE.md` §8](PROVENANCE.md#8-first-party-patches-ceralive)). Fixes a bookkeeping defect in `0001`, so its upstream position is the `0001` row's. Upstream Linux counterpart: **N/A** | `first-party-no-upstream` — upstream rkvenc is `WIP` (Collabora's Mesa/Vulkan work, the same tracker as `0001`), and there is no upstream VEPU580 H.264 driver to backport a fix from | Only if `0001` itself retires, i.e. if an upstream VEPU580 driver ever replaces it wholesale. **Do not retire it on the strength of "upstream rkvenc landed"** — see [§ `0001`](#0001--do-not-retire-on-rkvenc-landing), which applies verbatim | 2026-08-08 | Adds `dma_set_max_seg_size(dev, DMA_BIT_MASK(32))` to `rkvenc_hw_probe()`, then **reads it back** with `dma_get_max_seg_size()` and fails the probe with `-EINVAL` if it did not take. Defect 2 of the 3 stacked in the pipeline's "MPP hardware video encode" KNOWN ISSUE. The IOVA guardrail in `rkvenc_service.c` is **deliberately untouched** — it correctly catches the symptom. Read [§ `0008`](#0008--unvalidated-and-what-that-does-and-does-not-mean) |

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

This is the one row that must not be read quickly.

> **Corrected 2026-08-08 by T10.** An earlier revision of this row called the
> 7.2-rc1 counterpart *"different work"* from `7dd27810eea0`. **It is not — they
> are the same commit in two trees.** The correction, with sources, is in
> [§ Resolution](#resolution--they-are-the-same-commit) below and in full in
> [`EVAL-0002-EDID.md`](EVAL-0002-EDID.md).

**Fact 1 — an upstream EDID fix is merged for 7.2-rc1.** The Collabora capture
lists "HDMI-RX EDID fix (7.2-rc1)", PATCHv2 by Dmitry Osipenko:
<https://lore.kernel.org/r/20260325105742.63236-1-dmitry.osipenko@collabora.com>.
That is the counterpart T10 was chartered to evaluate `0002` against. Note that
"HDMI-RX EDID fix" is the Collabora table's own label — it names the *symptom*.
The patch's actual subject is *"media: synopsys: hdmirx: Fix HPD lane hold time"*,
and that mismatch is where the confusion below came from.

**Fact 2 — stable already shipped a fix for the same symptom, and it is in our
base.** The T7 rebase found exactly one commit in the whole 744-commit
`v7.1.5..v7.1.7` window touching anything this series touches:

```
commit 7dd27810eea05554d9b43f74022bee9b37a86ac4   (first appears in v7.1.6)
    media: synopsys: hdmirx: Fix HPD lane hold time
    commit d1162a5adbb5e95953d460b5bde3a04cd4473fe9 upstream.
    Reported-by: Ross Cawston <ross@r-sc.ca>
    Closes: https://lore.kernel.org/r/20260209061654.54757-1-ross@r-sc.ca
```

It changes two lines inside `hdmirx_hpd_ctrl()` — `msleep(100)` → `msleep(100 + 50)`
— and its commit message names the *same* symptom `0002` exists to fix, "EDID
change not detected by source/display side". It is **Reported-by Ross Cawston**,
the author of `0001`–`0005`, and it `Closes:` his own posting dated **2026-02-09**,
the same date `0002` carries.

**What is settled.** It is not a rebase problem. `0002` only *adds call sites* to
`hdmirx_hpd_ctrl()` and rewires the EDID-write, signal-lock and DMA-reset paths;
it shares no line with the stable fix, and being net-zero lines the stable fix did
not even shift a hunk offset. `0002` applies at `v7.1.7` with offsets only, and
the content check shows none of its own symbols (`WAIT_SIGNAL_LOCK_TIME`,
`NO_LOCK_CFG_RETRY_TIME`, `WAIT_LOCK_STABLE_TIME`) exist in the base.

**What is NOT settled, and is the open, hardware-gated question T7 ledgered:**

> With `7dd27810eea0` in the base, is `0002`'s plugout/IRQ/HPD sequence still
> required for a source to re-read a written EDID, or is the +50 ms hold now
> sufficient on its own?

Nobody has answered it, because answering it needs a real HDMI source and an
RK3588 board, and this repository gates patch application only. The full write-up
is [`REBASE-v7.1.7.md` § Stable overlap](REBASE-v7.1.7.md#stable-overlap--7dd27810eea0-and-why-it-is-not-a-conflict).

### Resolution — they are the same commit

T10 disambiguated this on 2026-08-08. There are **not** two upstream answers.
There is one, and it has been in our base since `v7.1.6`:

- The Message-ID `20260325105742.63236-1-dmitry.osipenko@collabora.com` resolves
  (patchwork id `14494411`, project `linux-rockchip`) to
  **`[v2] media: synopsys: hdmirx: Fix HPD lane hold time`** — not to a separately
  titled EDID series.
- That posting is mainline **`d1162a5adbb5`** (author date `2026-03-25T10:57:42Z`
  matches the posting to the second; committed by Hans Verkuil 2026-05-05).
  Containment check against mainline: `v7.2-rc1` contains it, `v7.1` does not.
- `7dd27810eea0`'s own second line reads `commit d1162a5adbb5… upstream.` — the
  stable-backport marker. It **is** that commit, picked up via `Cc: stable`.

So "the 7.2-rc1 EDID fix" and "the stable HPD-hold-time fix" are one two-line
change in two trees, and we already carry it. The February/March gap that looked
like two efforts is simply report-then-fix: Ross Cawston reported the symptom on
2026-02-09, Collabora fixed it in March.

**Consequence — evaluated, and the answer is KEEP.** Adoption is not merely
rejected, it is impossible: the counterpart applies to `v7.1.7` as a **no-op**
(forward `git apply --check` fails, reverse succeeds, `--3way` yields an empty
diff). It also does not overlap `0002` — 2 lines of HPD-hold duration versus
`0002`'s 8 hunks of IRQ masking, lock-loop rework, phy retry and DMA reset. The
full verdict, against all five criteria, is [`EVAL-0002-EDID.md`](EVAL-0002-EDID.md).

**What this does not resolve.** The hardware-gated question above is unchanged.
Knowing the +50 ms hold is the *only* upstream answer narrows it; it does not
settle it. No board was involved in this evaluation, and none of it is
board-verified. The standing bar applies and is quoted in the verdict doc: the
in-house `0002` "is already working very well", so the threshold for replacing it
is high — and nothing came close to it.

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

### `0008` — `UNVALIDATED`, and what that does and does not mean

`0008` is the first series member to carry an explicit `UNVALIDATED` marker, in
its own mail header and in its row above. It is worth being precise about the
claim, because the patch is unusually well-grounded for something unproven.

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

**What is NOT established.** That the fix makes hardware encode work. It cannot,
on its own: the KNOWN ISSUE names **three** stacked defects and this is one of
them. The other two are userspace/heap problems that no patch in this repository
addresses — `librockchip-mpp` hard-codes a `system-uncached` dma-heap that mainline
does not register, and mainline has no uncached heap for it to fall back to. So a
correct `0008` is necessary and is certainly not sufficient, and no observation of
`rkvenc` behaviour on a board has been made with it applied.

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

**What would clear the marker.** A board with the series applied, `mpph264enc`
reachable, and the `guardrail: … outside iova` line absent from a real encode —
which in practice requires defects 1 and 3 to be addressed first. Until then this
row stays `UNVALIDATED` and nothing should describe the edge-track encoder as
working.

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

The first of the two first-party encoder patches, `dma_set_max_seg_size()` in the
rkvenc probe, **has landed as `0008`** and is now a row in
[§ Current series members](#current-series-members): `first-party-no-upstream`,
`UNVALIDATED` on hardware, upstream position inherited from the `0001` row (WIP
rkvenc, tracked only). The second — the `system-uncached` dma-heap port — is not
written and is deliberately not scheduled here: ARM cache-alias handling done
subtly wrong yields silent intermittent corruption in the video path, so it needs a
validation campaign rather than a patch.

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
