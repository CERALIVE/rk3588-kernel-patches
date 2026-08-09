# Rebase ledger — upstream `v6.19-rc8` → CeraLive target `v7.1.7`

Upstream developed and tested this series against `v6.19-rc8` (its own
`README.MD` says so). CeraLive targets the Armbian rk3588 **edge** kernel, which
resolves to `7.1` — see [`kernel-pin.env`](../kernel-pin.env) and
[`PREFLIGHT.md`](PREFLIGHT.md) for how that was derived.

This is the ledger for the move **from the previous base `v7.1.5` to `v7.1.7`**.
It supersedes [`REBASE-v7.1.5.md`](REBASE-v7.1.5.md), which stays in the tree as
the record of the earlier base.

| | |
|---|---|
| Previous base | `v7.1.5` = `155b42bec9cbb6b8cdc47dd9bd09503a81fbe493` |
| **This base** | **`v7.1.7`**, tag object `c8fde2689e91a16e9d4b11fe3b08e45c89870585`, commit `c7ba9d6de43e9d9bd755b1f3c19501a38898c6b6` |
| Stable commits in the window | 744 (`git rev-list --count v7.1.5..v7.1.7`) |
| Rules file | [`rebase/v7.1.7.rules`](../rebase/v7.1.7.rules) |
| Result | **all 5 members apply, `git am` exit 0**, zero fuzz, zero rejects |

## The rule this document exists to enforce

> A conflict may be resolved here **only** if the resolution changes how a patch
> *applies*, never what it *does*. Anything requiring a judgement about driver
> behaviour is written down and stopped, not guessed at.

That rule is enforced by three mechanisms, not by good intentions:

1. `rebase/v7.1.7.rules` can only express context edits. `scripts/build-series.py`
   raises if a rule's anchor resolves to a `+` or `-` line, or if it is ambiguous.
2. `scripts/verify-payload-parity.py` compares the ordered set of `+`/`-` lines in
   `patches/` against each patch's own source lane and requires byte equality.
3. Both run in CI on every push and pull request, and in `scripts/apply.sh` before
   it will apply anything.

---

## Series membership — all FIVE members, and the `0004` gap

The series has **five** members. `0004` is a **deliberate ordinal gap, not a
member**: upstream never published a `0004`, and this fork preserves upstream's
numbering verbatim rather than renumbering to close it. The gap is asserted in
code, not just in prose — `scripts/build-series.py` sets `SERIES_TOTAL = 6` with
the comment "Slot count, not member count. 0004 was never published upstream and
we keep the gap so our files line up 1:1 with theirs, hence ordinals 1/6, 2/6,
3/6, 5/6, 6/6", and its module docstring repeats it: "Upstream numbering
(0001/0002/0003/0005, gap at 0004) is never renumbered". `patches/series` carries
the same note as a generated comment.

> **Why this section is spelled out.** The previous ledger,
> [`REBASE-v7.1.5.md`](REBASE-v7.1.5.md), enumerated only four patches — it
> omitted `0006`, the first-party `ceralive/` member, and its summary line reads
> "`git am` applies all four patches". That was an under-count of the series, not
> a statement about the gap. This ledger covers **5/5**.

| Ordinal | Patch | Lane | Member? |
|---|---|---|---|
| `0001` | `0001-rockchip-rk3588-vepu580-encoder-support-v3.patch` | `upstream/` | yes |
| `0002` | `0002-rockchip-rk3588-hdmirx-edid-fix-v1.patch` | `upstream/` | yes |
| `0003` | `0003-rockchip-rk3588-hdmirx-plugout-fix-v1.patch` | `upstream/` | yes |
| *0004* | — | — | **no — deliberate gap, never published upstream** |
| `0005` | `0005-rockchip-rk3588-hdmirx-audio.patch` | `upstream/` | yes |
| `0006` | `0006-rk3588-hdmirx-audio-sound-card.patch` | `ceralive/` | yes (first-party) |

---

## Summary

| Patch | Hunks | Files | Clean at `v7.1.7` | Action |
|-------|-------|-------|-------------------|--------|
| `0001` vepu580 encoder | 15 | 13 | 14 of 15 | 1 context re-anchor (**R1**) |
| `0002` hdmirx EDID | 8 | 1 | 8 of 8 (offsets only) | none |
| `0003` hdmirx plugout | 2 | 1 | 2 of 2 (offsets only) | none |
| `0005` hdmirx audio | 18 | 3 | 17 of 18 | 1 context re-anchor (**R2**) |
| `0006` hdmirx sound card | 5 | 3 | 5 of 5 (no offsets) | none |
| **Stopped for behavioural judgement** | — | — | — | **none** |

Result: `git am` applies all **five** patches to `v7.1.7` with exit 0. Transcript
in [§ Verification](#verification).

**Both rules carried over from `v7.1.5` unchanged — but neither was carried on
faith.** `REBASE-v7.1.5.md` warns that a rule right for one tag may be wrong for
the next, so each was re-decided against the v7.1.7 tree (§R1, §R2) and both were
re-proven load-bearing by a counterfactual run (§ Non-vacuity). The regenerated
`patches/` therefore differ from the `v7.1.5` generation only in mail-header text
and the `patches/series` target-kernel stamp; not one context line, added line or
removed line moved.

---

## Per-hunk disposition

Offsets below are as reported by GNU `patch -p1 -F0` applying the generated
`patches/*.patch` **sequentially** into a tree at `v7.1.7` — the same cumulative
state `git am` sees. `-F0` forbids fuzz, so every hunk below matched its context
exactly; only its line number moved. A hunk not listed as moved landed at
offset 0. Full log: [§ Verification](#verification).

### `0001` — vepu580 encoder · 15 hunks across 13 files

| File | Hunks | Disposition |
|---|---|---|
| `arch/arm64/boot/dts/rockchip/rk3588-base.dtsi` | 2 | #1 clean, offset 0. **#2 `@@ -1351,6 +1353,92 @@` — context re-anchor R1**, then applies at offset +64 |
| `drivers/iommu/rockchip-iommu.c` | 2 | clean, offset 0 |
| `drivers/media/platform/rockchip/Kconfig` | 1 | clean, offset 0 |
| `drivers/media/platform/rockchip/Makefile` | 1 | clean, offset 0 |
| `drivers/media/platform/rockchip/rkvenc/Kconfig` | 1 | new file — no anchor to drift |
| `drivers/media/platform/rockchip/rkvenc/Makefile` | 1 | new file |
| `drivers/media/platform/rockchip/rkvenc/rkvenc_drv.c` | 1 | new file |
| `drivers/media/platform/rockchip/rkvenc/rkvenc_hw.c` | 1 | new file |
| `drivers/media/platform/rockchip/rkvenc/rkvenc_hw.h` | 1 | new file |
| `drivers/media/platform/rockchip/rkvenc/rkvenc_iommu.c` | 1 | new file |
| `drivers/media/platform/rockchip/rkvenc/rkvenc_service.c` | 1 | new file |
| `drivers/media/platform/rockchip/rkvenc/rkvenc_task.c` | 1 | new file |
| `include/uapi/linux/rkvenc.h` | 1 | new file |

Nine of the fifteen hunks create files that do not exist at `v7.1.7`
(§ Patch-ID / content check), so they have no context to lose. The ~4,200 lines of
ported vendor driver code are entirely inside those nine.

### `0002` — hdmirx EDID · 8 hunks, one file

`drivers/media/platform/synopsys/hdmirx/snps_hdmirx.c`

| Hunk | Disposition |
|---|---|
| #1 | clean, offset 0 |
| #2 | clean, offset +2 (at 626) |
| #3 | clean, offset +2 (at 687) |
| #4 | clean, offset +48 (at 2151) |
| #5 | clean, offset +48 (at 2162) |
| #6 | clean, offset +48 (at 2181) |
| #7 | clean, offset +48 (at 2204) |
| #8 | clean, offset +48 (at 2219) |

No rule. See § Stable overlap for the one thing about `0002` that *did* change in
this window and is deliberately **not** a conflict.

### `0003` — hdmirx plugout · 2 hunks, one file

`drivers/media/platform/synopsys/hdmirx/snps_hdmirx.c`

| Hunk | Disposition |
|---|---|
| #1 | clean, offset +2 (at 621) |
| #2 | clean, offset +2 (at 643) |

No rule.

### `0005` — hdmirx audio · 18 hunks across 3 files

| File | Hunk | Disposition |
|---|---|---|
| `…/hdmirx/Kconfig` | #1 | clean, offset 0 |
| `…/hdmirx/snps_hdmirx.c` | #1 | clean, offset 0 |
| | #2 | clean, offset 0 |
| | **#3** | **context re-anchor R2** — `@@ -135,7 +148,13 @@` widened to `@@ -135,8 +148,14 @@`; then applies at offset 0 |
| | #4 | clean, offset +2 (at 638) |
| | #5 | clean, offset +2 (at 1020) |
| | #6 | clean, offset +48 (at 2632) |
| | #7 | clean, offset +48 (at 2689) |
| | #8 | clean, offset +44 (at 2719) |
| | #9 | clean, offset +79 (at 3150) |
| | #10 | clean, offset +82 (at 3209) |
| | #11 | clean, offset +82 (at 3233) |
| | #12 | clean, offset +82 (at 3251) |
| `…/hdmirx/snps_hdmirx.h` | #1–#5 | clean, offset 0 (all five) |

### `0006` — hdmirx audio sound card (first-party) · 5 hunks across 3 files

| File | Hunks | Disposition |
|---|---|---|
| `arch/arm64/boot/dts/rockchip/rk3588-extra.dtsi` | 2 | clean, offset 0 |
| `arch/arm64/boot/dts/rockchip/rk3588-orangepi-5-plus.dts` | 2 | clean, offset 0 |
| `arch/arm64/boot/dts/rockchip/rk3588-rock-5b.dtsi` | 1 | clean, offset 0 |

No rule, and no offsets at all: no commit in `v7.1.5..v7.1.7` touches any of the
three device-tree files, and `0006` was authored against this same `7.1` line.

---

## R1 — `0001`, `rk3588-base.dtsi`, hunk `@@ -1351,6 +1353,92 @@`

**Symptom** (reproduced at `v7.1.7`, applying the raw `upstream/` file with no
rules — see § Non-vacuity):

```
Hunk #2 FAILED at 1353.
1 out of 2 hunks FAILED -- saving rejects to file
arch/arm64/boot/dts/rockchip/rk3588-base.dtsi.rej
```

**What the hunk does.** It inserts six new device-tree nodes — `mpp_srv`,
`rkvenc_ccu`, `rkvenc0`, `rkvenc0_mmu`, `rkvenc1`, `rkvenc1_mmu` — immediately
before the existing `av1d` node. It is pure insertion: 86 added lines, zero
removed lines.

**Why it stopped applying.** The hunk's leading anchor is the closing three lines
of the **neighbouring** `vdec1_mmu` node, which the patch never modifies. Between
`v6.19-rc8` and the `7.1` line, mainline re-pointed that node from the shared VDPU
power domain to its own:

```diff
-		power-domains = <&power RK3588_PD_VDPU>;
+		power-domains = <&power RK3588_PD_RKVDEC1>;
```

The anchor text changed, so the hunk lost its position. Nothing about the encoder
work is involved.

**Why this is anchor drift and not a behavioural conflict — re-checked at
`v7.1.7`, not inherited from the `v7.1.5` ledger:**

1. `git log --oneline v7.1.5..v7.1.7 -- arch/arm64/boot/dts/rockchip/rk3588-base.dtsi`
   returns **nothing**: mainline did not touch this file again in the window, so
   the drift is exactly the one already known.
2. Nothing the hunk **adds** mentions `RK3588_PD_VDPU`. The added `rkvenc*` nodes
   use `RK3588_PD_VENC0` / `RK3588_PD_VENC1`.
3. Every dt-binding symbol the added nodes reference still exists at `v7.1.7`:
   `RK3588_PD_VENC0`, `RK3588_PD_VENC1`; `ACLK_RKVENC0/1`, `HCLK_RKVENC0/1`,
   `CLK_RKVENC0/1_CORE`; `SRST_A_RKVENC0/1`, `SRST_H_RKVENC0/1`,
   `SRST_RKVENC0/1_CORE`. All fourteen verified present.
4. No collision: `v7.1.7` defines no `mpp_srv:` / `rkvenc_ccu:` / `rkvenc0:` /
   `rkvenc1:` node label in `rk3588-base.dtsi`, has no
   `drivers/media/platform/rockchip/rkvenc/` directory, and no
   `include/uapi/linux/rkvenc.h`.
5. After applying, `vdec1_mmu` still reads
   `power-domains = <&power RK3588_PD_RKVDEC1>;` — mainline's current value
   survives; the resolution does not overwrite it with the stale one.

**Resolution.** One `replace` rule updating the context line to mainline's current
text. Zero added or removed lines change. Because `replace` is 1-for-1, the hunk
header is untouched.

---

## R2 — `0005`, `snps_hdmirx.c`, hunk `@@ -135,7 +148,13 @@`

**Symptom** (reproduced at `v7.1.7` with no rules):

```
Hunk #3 FAILED at 148.
1 out of 12 hunks FAILED -- saving rejects to file
drivers/media/platform/synopsys/hdmirx/snps_hdmirx.c.rej
```

**What the hunk does.** Adds six members to `struct snps_hdmirx_dev`:
`delayed_work_audio` before `cec`, then `audio_state`, `codec_dev`, `plugged_cb`,
`aud_clk`, `audio_present` after it.

**Why it stopped applying.** Mainline added a member in exactly the gap the hunk
anchors on. Read out of `v7.1.7` directly:

```c
	struct hdmirx_cec *cec;
	struct mutex phy_rw_lock; /* to protect phy r/w configuration */   /* mainline */
	struct mutex stream_lock; /* to lock video stream capture */
```

**Still correct at `v7.1.7`.** The only commit touching this file in the window,
`7dd27810eea0`, changed `hdmirx_hpd_ctrl()` and nothing else — the struct is
byte-for-byte what the `v7.1.5` rule was written against, so the same one-line
`insert-before` is still the right and sufficient fix.

**Resolution.** One `insert-before` rule that reintroduces `phy_rw_lock` as a
context line ahead of `stream_lock`, widening the hunk's old/new counts by one:
`@@ -135,7 +148,13 @@` → `@@ -135,8 +148,14 @@`. Zero added or removed lines
change.

### The one placement decision

Re-anchoring forces a choice: do the patch's new members go **before** or
**after** mainline's `phy_rw_lock`? They are kept where the patch put them —
immediately after `cec` — so `phy_rw_lock` now follows them. Resulting order:

```c
	struct delayed_work delayed_work_res_change;
	struct delayed_work delayed_work_audio;      /* patch */
	struct hdmirx_cec *cec;
	struct hdmirx_audiostate audio_state;        /* patch */
	struct device *codec_dev;                    /* patch */
	hdmi_codec_plugged_cb plugged_cb;            /* patch */
	struct clk *aud_clk;                         /* patch */
	int audio_present;                           /* patch */
	struct mutex phy_rw_lock;                    /* mainline */
	struct mutex stream_lock;
```

**Why this is behaviour-neutral, not a judgement call about the driver.**
`struct snps_hdmirx_dev` is a private driver structure. It is not UAPI, not
`__packed`, never serialised to hardware or userspace, and no member is reached by
computed offset — every access is by name. Member order therefore has no
observable effect on what the driver does. The alternative ordering would compile
to an equally correct driver. The chosen ordering preserves the patch author's
stated intent ("these go right after `cec`") and keeps the rule to a single-line
insertion.

This is recorded here rather than left implicit precisely because it is the only
point in the whole rebase where more than one correct answer existed. It is the
same decision the `v7.1.5` ledger recorded, re-affirmed rather than re-litigated,
because the surrounding code did not change.

---

## Patch-ID / content check against the new base

A hunk that still applies proves nothing about whether stable has meanwhile
absorbed the *fix*. Two independent checks were run per patch:

1. **Path check** — `git log --oneline v7.1.5..v7.1.7 -- <every path the patch
   touches>`.
2. **Content check** — grep the `v7.1.7` tree for the symbols, functions and
   nodes each patch introduces, so an absorbed change shows up even if it landed
   through a different path or a different commit.

### Path check

| Patch | Paths | Commits in `v7.1.5..v7.1.7` |
|---|---|---|
| `0001` | `rk3588-base.dtsi`, `drivers/iommu/rockchip-iommu.c`, `rockchip/{Kconfig,Makefile}`, `rockchip/rkvenc/`, `include/uapi/linux/rkvenc.h` | **none** |
| `0002` | `synopsys/hdmirx/snps_hdmirx.c` | `7dd27810e` |
| `0003` | `synopsys/hdmirx/snps_hdmirx.c` | `7dd27810e` |
| `0005` | `synopsys/hdmirx/{Kconfig,snps_hdmirx.c,snps_hdmirx.h}` | `7dd27810e` |
| `0006` | `rk3588-extra.dtsi`, `rk3588-orangepi-5-plus.dts`, `rk3588-rock-5b.dtsi` | **none** |

Exactly one stable commit lands anywhere near this series in the whole 744-commit
window. It is analysed in § Stable overlap.

### Content check — nothing was absorbed

| Patch | Probe at `v7.1.7` | Result |
|---|---|---|
| `0001` | `drivers/media/platform/rockchip/rkvenc/` directory | absent |
| | `include/uapi/linux/rkvenc.h` | absent |
| | node labels `mpp_srv:` `rkvenc_ccu:` `rkvenc0:` `rkvenc1:` in `rk3588-base.dtsi` | absent |
| | 14 dt-binding symbols the added nodes need | all present (nothing to port) |
| `0002` | `WAIT_SIGNAL_LOCK_TIME`, `NO_LOCK_CFG_RETRY_TIME`, `WAIT_LOCK_STABLE_TIME` | all absent |
| | the loop `0002` rewrites: `for (i = 0; i < 300; i++)` / `if (i == 300)` | still present, unmodified |
| `0003` | `vb2_queue_error` anywhere under `synopsys/hdmirx/` | absent |
| | `hdmirx_plugout()` body | still has no `stream` local and no vb2 error signalling |
| `0005` | `HDMI_CODEC_DRV_NAME`, `hdmi_codec_pdata`, `hdmirx_audio*`, `delayed_work_audio`, `audio_state`, `aud_clk`, `audio_present`, `plugged_cb`, `codec_dev`, `SND_SOC` | all absent |
| | `synopsys/hdmirx/Kconfig` | no ASoC `select`; unchanged |
| `0006` | `hdmirx_sound` / `hdmirx-sound` / `hdmirx_codec_dai` in `arch/arm64/boot/dts/rockchip/` | absent |
| | `#sound-dai-cells` inside the `hdmi_receiver` node of `rk3588-extra.dtsi` | absent |
| | `&i2s7_8ch { }` on either CeraLive board | not enabled |
| | `&hdmi_receiver { }` on either CeraLive board | enabled — so the silent no-capture-card state `0006` fixes is still exactly reproducible at `v7.1.7` |

**Verdict: 0 of 5 patches have been partially or wholly absorbed by stable.**

---

## Stable overlap — `7dd27810eea0`, and why it is *not* a conflict

This is the one finding in the window that a reader must not skim.

```
commit 7dd27810eea05554d9b43f74022bee9b37a86ac4   (first tag: v7.1.6)
    media: synopsys: hdmirx: Fix HPD lane hold time
    commit d1162a5adbb5e95953d460b5bde3a04cd4473fe9 upstream.

    Increase time of holding HPD lane low by 50ms. This fixes EDID change not
    detected by source/display side.

    Fixes: 7b59b132ad43 ("media: platform: synopsys: Add support for HDMI input driver")
    Cc: stable@vger.kernel.org
    Reported-by: Ross Cawston <ross@r-sc.ca>
    Closes: https://lore.kernel.org/linux-rockchip/20260209061654.54757-1-ross@r-sc.ca/
```

```diff
@@ -506,9 +506,9 @@ static void hdmirx_hpd_ctrl(struct snps_hdmirx_dev *hdmirx_dev, bool en)
 	hdmirx_writel(hdmirx_dev, CORE_CONFIG,
 		      hdmirx_dev->hpd_trigger_level_high ? en : !en);
 
-	/* 100ms delay as per HDMI spec */
+	/* 100ms delay as per HDMI spec + extra 50ms to cover internal delay */
 	if (!en)
-		msleep(100);
+		msleep(100 + 50);
 }
```

**Why it matters.** It is reported by **Ross Cawston** — the author of `0001`–
`0005` — against the *same* symptom `0002` exists to fix ("EDID change not
detected by source/display side"), and the `Closes:` link is his own
2026-02-09 posting, the same day `0002` is dated. Stable has therefore shipped
*an* upstream answer to the problem `0002` attacks.

**Why it is nevertheless not a conflict, and not a stop.**

- **Different code.** The stable fix rewrites two lines *inside* `hdmirx_hpd_ctrl()`.
  `0002` never modifies that function's body — it only adds two **call sites** to
  it (in `hdmirx_plugout()` and `hdmirx_delayed_work_hotplug()`) and rewires the
  EDID-write path, the signal-lock loop and the DMA reset. There is no line in
  common, hence no hunk conflict: `0002` applies at `v7.1.7` with offsets only.
- **Different fix.** The stable fix lengthens one delay. `0002` forces a full
  plugout/HPD-low sequence with IRQs disabled around the EDID write and re-queues
  the hotplug work. They stack; neither reverts the other.
- **Nothing to un-apply.** The content check above shows none of `0002`'s own
  symbols or edits are present at `v7.1.7`.

**What is deliberately NOT claimed.** This ledger does **not** claim `0002` is
still necessary now that the stable fix exists, nor that the two are optimally
combined. Deciding that is a behavioural judgement about the driver, it needs a
real HDMI source and an RK3588 board, and this repository gates patch application
only. It is recorded here as an open question for whoever gets hardware:

> **Open question (hardware-gated).** With `7dd27810eea0` in the base, is
> `0002`'s plugout/IRQ/HPD sequence still required for a source to re-read a
> written EDID, or is the +50 ms hold now sufficient on its own? If it is
> sufficient, `0002` becomes a retirement candidate
> (`retired/REGISTRY.md`) rather than a rebase problem. Do not act on this
> without a board.

---

## Non-vacuity — proof both rules are still load-bearing at `v7.1.7`

A rules file that has quietly become unnecessary is worse than none: it looks like
diligence while re-anchoring nothing. So the counterfactual was run — the raw
source-lane files, with **no** rules applied, against a clean `v7.1.7` tree:

```
########## 0001-rockchip-rk3588-vepu580-encoder-support-v3.patch   (upstream/)
patching file arch/arm64/boot/dts/rockchip/rk3588-base.dtsi
Hunk #2 FAILED at 1353.
1 out of 2 hunks FAILED -- saving rejects to file arch/arm64/boot/dts/rockchip/rk3588-base.dtsi.rej
   exit=1
########## 0002-rockchip-rk3588-hdmirx-edid-fix-v1.patch           (upstream/)
   exit=0
########## 0003-rockchip-rk3588-hdmirx-plugout-fix-v1.patch        (upstream/)
   exit=0
########## 0005-rockchip-rk3588-hdmirx-audio.patch                 (upstream/)
patching file drivers/media/platform/synopsys/hdmirx/snps_hdmirx.c
Hunk #3 FAILED at 148.
1 out of 12 hunks FAILED -- saving rejects to file drivers/media/platform/synopsys/hdmirx/snps_hdmirx.c.rej
   exit=1
########## 0006-rk3588-hdmirx-audio-sound-card.patch               (ceralive/)
   exit=0
```

Exactly two hunks fail without rules, and they are exactly the two hunks R1 and R2
address. No third rule is needed, and neither existing rule is dead weight.

---

## Stopped for behavioural judgement

**None.** Both conflicts were context-anchor drift, and both were already known
from the `v7.1.5` base; `v7.1.5 → v7.1.7` introduced no new conflict of any kind.

The one thing stable *did* change in this area — `7dd27810eea0` — produces no hunk
conflict (§ Stable overlap) and is net zero lines, so it did not even shift an
offset. It is recorded above as an open, hardware-gated question rather than as a
resolution, because deciding it would require judging what the driver should do.

If a future kernel bump produces a conflict that cannot be re-anchored by context
alone — for example, one where mainline has changed a function signature, a lock
discipline, or a register layout the patch depends on — it belongs **here**, in
this section, hunk by hunk, and the series is reported as not applying. It does
**not** belong in `rebase/*.rules`. The encoder patch (`0001`) in particular
carries ~4,200 lines of ported vendor driver code; a real behavioural conflict in
it needs review by someone who can test on RK3588 hardware, not a plausible-looking
merge.

---

## Not covered by this ledger

This repository gates **patch application only**. Specifically **not** verified
here:

- **That the result compiles.** No `make` is run. The kernel build lives in the
  image pipeline.
- **That the driver works on hardware.** No RK3588 board is involved anywhere in
  this repository.
- **That the DT overlay binds.** `overlays/rockchip-rk3588-rkvenc-mpp.dts` is
  carried verbatim and is not applied or compiled by the gate.
- **Kernel config.** `CONFIG_VIDEO_ROCKCHIP_RKVENC` must be enabled by whoever
  builds; the gate only asserts the symbol is *selectable* after the patches land.
- **Whether `0002` is still needed** now that `7dd27810eea0` is in the base — see
  the open question in § Stable overlap.

---

## Verification

Reproduce with `scripts/apply.sh` — the same script CI runs. Recorded run,
2026-08-08, against `.work/linux` cloned from `KERNEL_MIRROR` at `v7.1.7`:

```
== Verifying patches/ is generated, not hand-edited
patches/ is in sync (6 files).

== Verifying the series changes nothing its source lanes did not already change
OK   0001-rockchip-rk3588-vepu580-encoder-support-v3.patch: 4414 payload lines identical to upstream/, dropped 8 .DS_Store stanza(s)
OK   0002-rockchip-rk3588-hdmirx-edid-fix-v1.patch: 41 payload lines identical to upstream/
OK   0003-rockchip-rk3588-hdmirx-plugout-fix-v1.patch: 13 payload lines identical to upstream/, dropped 1 .DS_Store stanza(s)
OK   0005-rockchip-rk3588-hdmirx-audio.patch: 455 payload lines identical to upstream/
OK   0006-rk3588-hdmirx-audio-sound-card.patch: 41 payload lines identical to ceralive/

all 5 patches: payload byte-identical to their source.

== Using existing kernel tree /…/rk3588-kernel-patches/.work/linux

== Kernel tree at v7.1.7 (tag c8fde2689e91a16e9d4b11fe3b08e45c89870585, commit c7ba9d6de43e9d9bd755b1f3c19501a38898c6b6)

== Applying 5 patches with git am
Applying: rockchip: rk3588: add VEPU580 (RKVENC v2) H.265/H.264/JPEG encoder support
Applying: media: synopsys: hdmirx: make a written EDID visible to the HDMI source
Applying: media: synopsys: hdmirx: fix buffer overflow on repeated HDMI-RX replug
Applying: media: synopsys: hdmirx: add HDMI-RX audio capture support
Applying: arm64: dts: rockchip: rk3588: bind the HDMI-RX audio codec to a sound card

== Applied cleanly
157281d24 arm64: dts: rockchip: rk3588: bind the HDMI-RX audio codec to a sound card
02874c290 media: synopsys: hdmirx: add HDMI-RX audio capture support
e6a53c283 media: synopsys: hdmirx: fix buffer overflow on repeated HDMI-RX replug
aea15e6c5 media: synopsys: hdmirx: make a written EDID visible to the HDMI source
7305c9a59 rockchip: rk3588: add VEPU580 (RKVENC v2) H.265/H.264/JPEG encoder support

 arch/arm64/boot/dts/rockchip/rk3588-base.dtsi      |   88 ++
 arch/arm64/boot/dts/rockchip/rk3588-extra.dtsi     |   25 +
 .../boot/dts/rockchip/rk3588-orangepi-5-plus.dts   |    8 +
 arch/arm64/boot/dts/rockchip/rk3588-rock-5b.dtsi   |    8 +
 drivers/iommu/rockchip-iommu.c                     |    2 +
 drivers/media/platform/rockchip/Kconfig            |    1 +
 drivers/media/platform/rockchip/Makefile           |    1 +
 drivers/media/platform/rockchip/rkvenc/Kconfig     |   17 +
 drivers/media/platform/rockchip/rkvenc/Makefile    |    2 +
 .../media/platform/rockchip/rkvenc/rkvenc_drv.c    |  481 ++++++++
 drivers/media/platform/rockchip/rkvenc/rkvenc_hw.c |  888 ++++++++++++++
 drivers/media/platform/rockchip/rkvenc/rkvenc_hw.h |  881 ++++++++++++++
 .../media/platform/rockchip/rkvenc/rkvenc_iommu.c  |  463 ++++++++
 .../platform/rockchip/rkvenc/rkvenc_service.c      | 1206 ++++++++++++++++++++
 .../media/platform/rockchip/rkvenc/rkvenc_task.c   |  300 +++++
 drivers/media/platform/synopsys/hdmirx/Kconfig     |    1 +
 .../media/platform/synopsys/hdmirx/snps_hdmirx.c   |  482 +++++++-
 .../media/platform/synopsys/hdmirx/snps_hdmirx.h   |   26 +
 include/uapi/linux/rkvenc.h                        |   84 ++
 19 files changed, 4958 insertions(+), 6 deletions(-)

== Post-apply checks
  ok      drivers/media/platform/rockchip/rkvenc/rkvenc_drv.c
  ok      drivers/media/platform/rockchip/rkvenc/rkvenc_service.c
  ok      include/uapi/linux/rkvenc.h
  ok      dts node mpp_srv
  ok      dts node rkvenc_ccu
  ok      dts node rkvenc0
  ok      dts node rkvenc1
  ok      CONFIG_VIDEO_ROCKCHIP_RKVENC is selectable
  ok      hdmirx registers an ASoC codec device
  ok      dts node hdmirx_sound
  ok      dts node hdmirx_codec_dai
  ok      hdmi_receiver is a sound-dai provider
  ok      rk3588-rock-5b.dtsi enables &hdmirx_sound
  ok      rk3588-rock-5b.dtsi enables &i2s7_8ch
  ok      rk3588-orangepi-5-plus.dts enables &hdmirx_sound
  ok      rk3588-orangepi-5-plus.dts enables &i2s7_8ch

== OK — series applies to v7.1.7
```

Whitespace hygiene of the applied result:

```
$ git -C .work/linux diff --check v7.1.7..HEAD
$ echo $?
0
```

Per-hunk offsets (the sequential GNU `patch -p1 -F0` run the disposition tables
above are drawn from; every hunk not printed landed at offset 0, and no hunk
needed fuzz or produced a `.rej`):

```
########## 0001-rockchip-rk3588-vepu580-encoder-support-v3.patch
patching file arch/arm64/boot/dts/rockchip/rk3588-base.dtsi
Hunk #2 succeeded at 1417 (offset 64 lines).
patching file drivers/iommu/rockchip-iommu.c
patching file drivers/media/platform/rockchip/Kconfig
patching file drivers/media/platform/rockchip/Makefile
patching file drivers/media/platform/rockchip/rkvenc/Kconfig
patching file drivers/media/platform/rockchip/rkvenc/Makefile
patching file drivers/media/platform/rockchip/rkvenc/rkvenc_drv.c
patching file drivers/media/platform/rockchip/rkvenc/rkvenc_hw.c
patching file drivers/media/platform/rockchip/rkvenc/rkvenc_hw.h
patching file drivers/media/platform/rockchip/rkvenc/rkvenc_iommu.c
patching file drivers/media/platform/rockchip/rkvenc/rkvenc_service.c
patching file drivers/media/platform/rockchip/rkvenc/rkvenc_task.c
patching file include/uapi/linux/rkvenc.h
   patch-exit=0
########## 0002-rockchip-rk3588-hdmirx-edid-fix-v1.patch
patching file drivers/media/platform/synopsys/hdmirx/snps_hdmirx.c
Hunk #2 succeeded at 626 (offset 2 lines).
Hunk #3 succeeded at 687 (offset 2 lines).
Hunk #4 succeeded at 2151 (offset 48 lines).
Hunk #5 succeeded at 2162 (offset 48 lines).
Hunk #6 succeeded at 2181 (offset 48 lines).
Hunk #7 succeeded at 2204 (offset 48 lines).
Hunk #8 succeeded at 2219 (offset 48 lines).
   patch-exit=0
########## 0003-rockchip-rk3588-hdmirx-plugout-fix-v1.patch
patching file drivers/media/platform/synopsys/hdmirx/snps_hdmirx.c
Hunk #1 succeeded at 621 (offset 2 lines).
Hunk #2 succeeded at 643 (offset 2 lines).
   patch-exit=0
########## 0005-rockchip-rk3588-hdmirx-audio.patch
patching file drivers/media/platform/synopsys/hdmirx/Kconfig
patching file drivers/media/platform/synopsys/hdmirx/snps_hdmirx.c
Hunk #4 succeeded at 638 (offset 2 lines).
Hunk #5 succeeded at 1020 (offset 2 lines).
Hunk #6 succeeded at 2632 (offset 48 lines).
Hunk #7 succeeded at 2689 (offset 48 lines).
Hunk #8 succeeded at 2719 (offset 44 lines).
Hunk #9 succeeded at 3150 (offset 79 lines).
Hunk #10 succeeded at 3209 (offset 82 lines).
Hunk #11 succeeded at 3233 (offset 82 lines).
Hunk #12 succeeded at 3251 (offset 82 lines).
patching file drivers/media/platform/synopsys/hdmirx/snps_hdmirx.h
   patch-exit=0
########## 0006-rk3588-hdmirx-audio-sound-card.patch
patching file arch/arm64/boot/dts/rockchip/rk3588-extra.dtsi
patching file arch/arm64/boot/dts/rockchip/rk3588-orangepi-5-plus.dts
patching file arch/arm64/boot/dts/rockchip/rk3588-rock-5b.dtsi
   patch-exit=0
```

Also green in the same session, ahead of `apply.sh`:

```
$ python3 scripts/build-series.py
wrote 5 patches + series to /…/rk3588-kernel-patches/patches
$ python3 scripts/build-series.py --check
patches/ is in sync (6 files).
$ python3 scripts/verify-payload-parity.py
all 5 patches: payload byte-identical to their source.
$ bash scripts/preflight.sh
PREFLIGHT OK — kernel-pin.env matches armbian/build @ 587b6f2c0a867859ca3f323f6008bee9e3ef1553
```

### What regenerating `patches/` actually changed

Nothing behavioural, and nothing contextual — the whole diff is the tag name in
generated mail-header prose plus the `patches/series` target-kernel stamp:

```
 patches/0001-rockchip-rk3588-vepu580-encoder-support-v3.patch | 4 ++--
 patches/0005-rockchip-rk3588-hdmirx-audio.patch               | 4 ++--
 patches/0006-rk3588-hdmirx-audio-sound-card.patch             | 2 +-
 patches/series                                                | 2 +-
 4 files changed, 6 insertions(+), 6 deletions(-)
```

`0002` and `0003` are byte-identical across the bump: they carry no rules and no
tag-bearing header line.

> **The trap this ordering avoids.** `build-series.py::load_rules()` returns `[]`
> for a missing `rebase/<tag>.rules` — it does not raise. Regenerating `patches/`
> *before* writing `rebase/v7.1.7.rules` would therefore have produced a green,
> self-consistent, silently **un-re-anchored** series, and nothing would have
> warned. `rebase/v7.1.7.rules` was written first, and the staleness of the
> committed `patches/` against it was the only signal that the rules had ever been
> dropped.

---

## When the pin moves

Bumping `KERNEL_TAG` in `kernel-pin.env` is the *only* supported way to retarget.
The procedure:

1. Re-run `scripts/preflight.sh --head` to confirm Armbian still maps rk3588
   `edge` to the kernel line you expect. Do not assume it does.
2. Update `KERNEL_TAG`, `KERNEL_TAG_OBJECT`, and `KERNEL_COMMIT` together.
3. Create `rebase/<new-tag>.rules` **before** regenerating anything, seeded from
   the old one but re-decided rule by rule against the new tree. Rules are per-tag
   on purpose — a rule that was right for `v7.1.7` may be wrong for the next tag,
   and a missing rules file fails open, not loud.
4. Run the patch-ID / content check against the new base (§ above) before trusting
   a clean apply. A patch can still apply perfectly after stable has absorbed the
   fix it carries.
5. Run `scripts/apply.sh`. For every conflict, decide *once*: context drift (rule)
   or behavioural (stop, and write it up in a new `docs/REBASE-<tag>.md`).
6. `scripts/build-series.py && scripts/verify-payload-parity.py` must both pass
   before the change is proposed.
7. Update the tag restatements in `README.md`, `AGENTS.md` and `docs/PREFLIGHT.md`
   in the **same** change — they claim the series applies to a specific tag, and
   that claim only becomes true when the rebase lands.
