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

The series has six members. `0004` is a deliberate ordinal gap — upstream never
published one — and is not a row here for the same reason it is not a patch.

| Patch | Origin | Upstream status | Retire trigger | Last checked | Notes |
|---|---|---|---|---|---|
| `0001` vepu580 encoder (v3) | `upstream/` lane — imported from [`rcawston/rockchip-rk3588-mainline-patches`](https://github.com/rcawston/rockchip-rk3588-mainline-patches) @ `e13a311`; ported from the Rockchip BSP MPP driver. Upstream Linux counterpart: **N/A** | `WIP` — Collabora's rkvenc work, tracked at <https://lore.kernel.org/r/082e1141c38205222a91abf13b1a97d9a00e117a.camel@collabora.com> | **None foreseeable — track only.** Do *not* retire when rkvenc lands: see [§ 0001](#0001--do-not-retire-on-rkvenc-landing) | 2026-08-08 | Collabora table: VEPU580 H.264 = `WIP`, H.265 = `TODO` |
| `0002` hdmirx EDID fix (v1) | `upstream/` lane — Ross Cawston, same import. Upstream counterpart is `d1162a5adbb5` "media: synopsys: hdmirx: Fix HPD lane hold time", PATCHv2, <https://lore.kernel.org/r/20260325105742.63236-1-dmitry.osipenko@collabora.com> — **orthogonal work, already in our base** as `7dd27810eea0` | `merged@7.2-rc1` (the counterpart) — **and backported to the base at `v7.1.6`** | **None from this counterpart.** Retire only if the hardware-gated question below is answered "150 ms hold suffices"; base version is irrelevant to it | 2026-08-08 | **Upstream version rejected: nothing to adopt** — `7dd27810eea0` *is* the 7.2-rc1 fix (stable backport of `d1162a5adbb5`), it is already applied, and it is a 2-line HPD-hold change that shares no mechanism with `0002`. **4K60 input capability reviewed 2026-08-08: verdict unchanged and reinforced** — the driver's built-in EDID caps at 4K30 (`SCDC_Present = 0`), so 4K60 needs a runtime `S_EDID` write, which is the path `0002` fixes; 7 hardware-only checks (B1–B7) parked for T15. Verdict: [`EVAL-0002-EDID.md`](EVAL-0002-EDID.md). Read [§ 0002](#0002--one-upstream-answer-already-in-the-base) |
| `0003` hdmirx plugout fix (v1) | `upstream/` lane — Ross Cawston, same import. Upstream counterpart: **N/A** — none found (see [§ Sources](#sources-checked-for-this-sweep)) | `fork-carried-no-upstream` | None defined. Re-check at every base bump via the content check in [`REBASE-v7.1.7.md` § Patch-ID / content check](REBASE-v7.1.7.md#patch-id--content-check-against-the-new-base); retire only if a tree absorbs the `vb2_queue_error` plugout fix | 2026-08-08 | Content check at `v7.1.7`: `vb2_queue_error` still absent under `synopsys/hdmirx/` |
| `0005` hdmirx audio | `upstream/` lane — Ross Cawston, same import. Upstream counterpart is the 4-patch series **`[PATCH v4 0/4] media: synopsys: hdmirx: add HDMI audio capture support`** by Igor Paunovic, <https://lore.kernel.org/r/20260721064115.64809-1-royalnet026@gmail.com> — same mechanism, *competing* DT half | `sent-v4` — fully reviewed, **not merged**; author pinged for pickup 2026-08-05, unanswered | Counterpart merges **and** base reaches that version **and** Rock 5B+ enablement exists **and** the multichannel / jack / plugout regressions are closed. All four | 2026-08-08 | **Upstream version rejected: adoptable but not strictly better** — applies cleanly to `v7.1.7`, but drops multichannel, jack reporting, plugout teardown and pre-capture clock lock, and its 4/4 enables the card on **Orange Pi 5 Plus only**. Verdict: [`EVAL-0005-AUDIO.md`](EVAL-0005-AUDIO.md). Read [§ 0005 / 0006](#0005--0006--the-pairing-is-load-bearing-and-upstream-does-not-replace-it) |
| `0006` hdmirx audio sound card | `ceralive/` lane — **first-party CeraLive**. Never submitted (no `Signed-off-by`, deliberately — see [`PROVENANCE.md` §8](PROVENANCE.md#8-first-party-patches-ceralive)). Upstream counterpart: **partial only** — v4 3/4 covers the SoC-level card, v4 4/4 covers Orange Pi 5 Plus; **nothing upstream covers Rock 5B+** | `first-party-no-upstream` | Only if an upstream HDMI-RX audio series lands its own DT sound card **and** enables it on Rock 5B+ *and* Orange Pi 5+. As of 2026-08-08 the posted series does not | 2026-08-08 | **T11 answer: NOT superseded, and NOT compatible.** `0006` and v4 3/4 edit the same two regions of `rk3588-extra.dtsi` and disagree on `#sound-dai-cells` (`<0>` vs `<1>`); `git apply --check` of `0006` onto an upstream-applied tree fails. Modelled on the BSP's `hdmiin-sound` wiring, expressed with mainline `simple-audio-card`; no BSP text copied |
| `0007` iommu dte-limit fix | `backports/` lane — **backported from mainline** `8d4346ecd4950ae08cc76a6de327c264e846758c` "iommu/rockchip: disable fetch dte time limit", Simon Xue via Sven Püschel (Pengutronix), PATCHv2, <https://lore.kernel.org/r/20260428-spu-iommudtefix-v2-1-f592f579e508@pengutronix.de> | `merged@7.2-rc1` — `Acked-by` Heiko Stuebner, applied by Joerg Roedel 2026-06-02. **Absent from the base**: it carries no `Fixes:` tag and no `Cc: stable`, so `7.1.y` never picked it up | **Drop when base ≥ `v7.2`.** The base absorbing it is the whole retire condition — there is no merit question left, it is already mainline | 2026-08-08 | Sets `BIT(31)` of `MMU_AUTO_GATING` in `rk_iommu_enable()`, the vendor workaround for the RK356x/RK3588 blocked-VOP-and-black-screen and RK3588 RGA3 hang. Base check at `v7.1.7`: `DISABLE_FETCH_DTE_TIME_LIMIT` absent, `RK_MMU_AUTO_GATING` present. Applies forward with **no fuzz and no context adaptation**; **zero prerequisite commits**. Fixes:-tag sweep over mainline found **no follow-up** |

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

| Candidate | Owning task | Origin | Upstream status | Retire trigger | Last checked | Notes |
|---|---|---|---|---|---|---|
| ~~HDMI-RX EDID fix (upstream counterpart to `0002`)~~ — **NOT IMPORTED** | T10 — **done** | <https://lore.kernel.org/r/20260325105742.63236-1-dmitry.osipenko@collabora.com> (PATCHv2) = mainline **`d1162a5adbb5e95953d460b5bde3a04cd4473fe9`** | `merged@7.2-rc1` — **and already in the base** as `7dd27810eea0` (`v7.1.6`) | n/a — nothing was imported | 2026-08-08 | **Upstream version rejected: already applied, and orthogonal.** It is the *same commit* as `7dd27810eea0`, not a second fix; it applies to `v7.1.7` as a no-op (reverse-apply check passes, `--3way` diff empty); and its 2-line HPD-hold change shares no mechanism with `0002`. `0002` is KEPT. Verdict: [`EVAL-0002-EDID.md`](EVAL-0002-EDID.md) |
| ~~HDMI Input Audio PATCHv4 (upstream counterpart to `0005`)~~ — **NOT IMPORTED** | T11 — **done** | <https://lore.kernel.org/r/20260721064115.64809-1-royalnet026@gmail.com> — `[PATCH v4 0/4] media: synopsys: hdmirx: add HDMI audio capture support`, Igor Paunovic, 4 patches | `sent-v4` — **not merged.** `Reviewed-by` Sebastian Reichel, Krzysztof Kozlowski and Dmitry Osipenko; `Tested-by` Dmitry on 2/4. Author pinged for media-tree pickup 2026-08-05, unanswered as of 2026-08-08 | n/a — nothing was imported | 2026-08-08 | **Upstream version rejected: adoptable, but not strictly better.** Applies clean to `v7.1.7` (all four, forward, no fuzz), so this is a merit rejection not a mechanical one. Drops multichannel, jack reporting, `hdmirx_plugout()` teardown and pre-capture clock lock; adds suspend support, capture-only DAI flags and an accepted binding. **`0006` answer: NOT superseded** — v4 4/4 enables the card on Orange Pi 5 Plus only, leaving Rock 5B+ with a bound codec and no ALSA card. Verdict: [`EVAL-0005-AUDIO.md`](EVAL-0005-AUDIO.md) |
| IOMMU "disable fetch dte time limit" — **IMPORTED as `0007`** | T12 — **done** | <https://lore.kernel.org/r/20260428-spu-iommudtefix-v2-1-f592f579e508@pengutronix.de> (PATCHv2) = mainline **`8d4346ecd4950ae08cc76a6de327c264e846758c`** | `merged@7.2-rc1` — **not in the base.** No `Fixes:` tag and no `Cc: stable`, so `7.1.y` will not pick it up on its own | **Drop when base ≥ `v7.2`** | 2026-08-08 | Now a series member — see the `0007` row in [§ Current series members](#current-series-members) |
| ~~I2S MCLK output gate clocks~~ — **NOT IMPORTED** | T12 — **done** | <https://lore.kernel.org/r/20260320-rk3588-mclk-gate-grf-v3-0-980338eacd2c@superkali.me> is **v3**; the version that merged is **v4**, <https://lore.kernel.org/r/20260419-rk3588-mclk-gate-grf-v4-0-513a42dd1dcc@superkali.me> — **5** commits: `56c2ca0ae7cb`, `28820fc7983b`, `32d1d88c4165`, `06c990bffdbe`, `02b9b0bb6269` | `merged@7.2-rc1` (all five; none in the base) | n/a — nothing was imported | 2026-08-08 | **Skipped on both stop conditions at once.** (1) **Prereq chain is 4 deep, over the 2-commit ceiling**: the payload `02b9b0bb6269` needs the clock IDs, the `grf_type_sys` lookup, `rockchip_clk_add_grf()` *and* the `SOC_CON6` offset, none of which `v7.1.7` has. (2) **The merged version is known-buggy and its fix has not landed** — see [§ MCLK](#i2s-mclk-gate-clocks--skipped-known-regression-on-rock-5b) |
| V4L2 HW usage stats (fdinfo) for rkvdec + hantro | T13 | <https://lore.kernel.org/r/20260617-v4l2-add-fdinfo-v2-0-d298e98ce06a@collabora.com> (PATCHv2) | `sent-v2` — not merged | Drop when merged upstream **and** base reaches that version | 2026-08-08 | Collabora "Improvements (pending)". Encode/decode observability |
| V4L2 stateless codec tracepoints | T13 | <https://lore.kernel.org/r/20260212162328.192217-1-detlev.casanova@collabora.com> (PATCHv1) | `sent-v1` — not merged | Drop when merged upstream **and** base reaches that version | 2026-08-08 | Collabora "Improvements (pending)" |
| PCIe System PM support | T13 | <https://lore.kernel.org/r/20260316-rockchip-pcie-system-suspend-v5-0-5bb5ad37d643@collabora.com> (PATCHv5) | `sent-v5` — not merged | Drop when merged upstream **and** base reaches that version | 2026-08-08 | Collabora "Improvements (pending)" |
| SCDC link-health → connector debugfs | T13 — **gated** | <https://lore.kernel.org/r/20260724-scdc-link-health-v9-0-bdda406d016d@collabora.com> (PATCHv9) | `sent-v9` — not merged | Drop when merged upstream **and** base reaches that version | 2026-08-08 | Import **only** if a production-safety evaluation passes (Kconfig deps, runtime overhead, and whether debugfs is even mounted on the shipped image). The verdict is recorded here either way |
| VDPU381 VP9 decode | tracked only — **do not import** | <https://lore.kernel.org/r/20260726-b4-add-rkvdec2-vp9-vdpu381-v1-0-180fb2d1f10c@gmail.com> (PATCHv1) | `sent-v1` — not merged | n/a — not carried | 2026-08-08 | Out of the chosen lane: a decode feature, not metrics/PM. Row exists so a future reader can see it was considered and excluded on purpose |
| VDPU381 multi-core (H.264/H.265) | tracked only — **do not import** | <https://lore.kernel.org/r/20260409-rkvdec-multicore-v1-0-62b316abf0f7@collabora.com> (PATCHv1) | `sent-v1` — not merged | n/a — not carried | 2026-08-08 | Same exclusion as the row above |

The two first-party encoder patches (`dma_set_max_seg_size()` in the rkvenc probe,
and the `system-uncached` dma-heap port) are added to the **current series** table
above by the tasks that author them, T14 and T15. Both will be
`first-party-no-upstream`, both `UNVALIDATED` on hardware, and the encoder's
upstream position is the `0001` row's: WIP rkvenc, tracked only.

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
