# Evaluation — `0002` hdmirx EDID fix vs its upstream counterpart

**Verdict: KEEP `0002`. There is nothing to adopt.**

The "upstream 7.2-rc1 EDID fix" and the stable commit `7dd27810eea0` that
[`REBASE-v7.1.7.md`](REBASE-v7.1.7.md) found in the base are **the same commit**.
The base already carries the entire upstream artifact, byte for byte, and it is a
two-line delay change that does not overlap `0002`'s mechanism in any way. No
backport is possible, because there is nothing left to backport.

| | |
|---|---|
| Evaluated | 2026-08-08 |
| **Revisited** | **2026-08-08 — 4K60 input capability. Verdict unchanged and REINFORCED; see [§ Revisited](#revisited-2026-08-08--4k60-input-capability)** |
| Base | `v7.1.7` (`kernel-pin.env`) |
| In-house patch | [`upstream/0002-rockchip-rk3588-hdmirx-edid-fix-v1.patch`](../upstream/0002-rockchip-rk3588-hdmirx-edid-fix-v1.patch) — Ross Cawston, 2026-02-09 |
| Upstream counterpart | `d1162a5adbb5e95953d460b5bde3a04cd4473fe9`, first release `v7.2-rc1` |
| Its stable backport | `7dd27810eea05554d9b43f74022bee9b37a86ac4`, first tag `v7.1.6` — **already in the base** |
| Series change | **none** — `patches/` untouched, `retired/` untouched |

> **Read the [§ Revisited](#revisited-2026-08-08--4k60-input-capability) section
> before acting on anything below.** The original evaluation (everything down to
> § Verdict) was written without knowing that both shipped boards are specified for
> **4K@60 HDMI input**. That fact does not change the verdict, but it changes how
> strongly it is held: `0002` turns out to be a *functional prerequisite* for 4K60
> on these boards, not merely a fix worth keeping. Nothing in the original text has
> been silently rewritten — the revisit is additive, and where it corrects an
> earlier framing it says so.

---

## The standing instruction this evaluation was held to

The user's instruction, quoted verbatim:

> **"in-house is already working very well"**

That sets the bar. A replacement had to be **strictly better**, not merely also
correct, and not merely more upstream-shaped. The paragraphs below apply that bar,
and the outcome does not even reach the point where it matters — the candidate
turned out to be a subset of the base rather than a competitor to `0002`.

---

## The disambiguation, first — because everything else depends on it

[`UPSTREAM-STATUS.md` § 0002](UPSTREAM-STATUS.md#0002--one-upstream-answer-already-in-the-base)
recorded an open question: are `7dd27810eea0` and the 7.2-rc1 EDID fix the same
work, different work that happens to overlap, or does one make `0002` moot? The
row itself asserted they were *"different work"*. **That assertion was wrong, and
this document corrects it.**

Three independent sources agree, and they agree on a commit SHA, not on a
description:

**1. The Message-ID resolves to a subject that is not about EDID at all.**
`patchwork.kernel.org`'s API record for
`20260325105742.63236-1-dmitry.osipenko@collabora.com` (patchwork id `14494411`,
project `linux-rockchip`):

```
name:      [v2] media: synopsys: hdmirx: Fix HPD lane hold time
submitter: Dmitry Osipenko <dmitry.osipenko@collabora.com>
date:      2026-03-25T10:57:42
```

The Collabora status table lists this row as *"HDMI-RX EDID fix (7.2-rc1)"*. That
is the table naming the **symptom** — the patch's own subject line is
*"Fix HPD lane hold time"*. The mismatch between the table's label and the
patch's subject is the entire origin of the confusion.

**2. The posting is mainline `d1162a5adbb5`.** Author, timestamp and diff match
exactly — the mainline commit's author date `2026-03-25T10:57:42Z` is the
posting's `Date: Wed, 25 Mar 2026 13:57:42 +0300` to the second. Committed by
Hans Verkuil on 2026-05-05 through the media tree. Containment checked against
the mainline tree: `v7.2-rc1` contains it (`0` behind), `v7.1` does not
(diverged). So `merged@7.2-rc1` is correct — for *this* commit.

**3. `7dd27810eea0` says so itself.** Its second line, read out of our own base:

```
    media: synopsys: hdmirx: Fix HPD lane hold time

    commit d1162a5adbb5e95953d460b5bde3a04cd4473fe9 upstream.
```

That is the standard stable-backport marker. `7dd27810eea0` **is**
`d1162a5adbb5`, picked up by `Cc: stable@vger.kernel.org` and released in
`v7.1.6`.

### Answer to the three-way question

> **Same work.** `7dd27810eea0` and the 7.2-rc1 "EDID fix" are one commit in two
> trees. There are not two upstream answers in play; there is one, and we have
> been carrying it since the base moved to `v7.1.6`.

> **It does not make `0002` moot** — see criterion 1. It also does not *prove*
> `0002` is still needed. That question is unchanged and still hardware-gated;
> re-labelling the commit does not answer it either way.

---

## Criterion 1 — mechanism and coverage delta

**Upstream (`d1162a5adbb5`)** — 1 file, 1 hunk, 2 added / 2 removed lines, entirely
inside `hdmirx_hpd_ctrl()`:

```diff
-	/* 100ms delay as per HDMI spec */
+	/* 100ms delay as per HDMI spec + extra 50ms to cover internal delay */
 	if (!en)
-		msleep(100);
+		msleep(100 + 50);
```

One knob: hold HPD low 50 ms longer.

**In-house (`0002`)** — 1 file, 8 hunks, 41 payload lines, four distinct
mechanisms, none of which touch `hdmirx_hpd_ctrl()`'s body:

| # | Mechanism | Where |
|---|---|---|
| 1 | HPD is driven low as part of teardown | new `hdmirx_hpd_ctrl(dev, false)` call in `hdmirx_plugout()` |
| 2 | EDID write is wrapped in a full plugout with **both IRQs disabled** (`hdmi_irq`, `dma_irq`), then a hotplug work item is re-queued 1 s later | EDID-write path |
| 3 | Signal-lock loop reworked: bound `300` → `WAIT_SIGNAL_LOCK_TIME 600`; requires `WAIT_LOCK_STABLE_TIME 20` *consecutive* good reads instead of one; re-runs `hdmirx_phy_config()` every `NO_LOCK_CFG_RETRY_TIME 300` iterations | lock loop |
| 4 | DMA reset added before format change, settle `msleep(50)` → `msleep(500)` | post-lock path |
| 5 | HPD is driven high as part of bring-up | new `hdmirx_hpd_ctrl(dev, true)` call in the hotplug path |

**Delta: the upstream fix is a strict subset of nothing.** It is not smaller
coverage of the same mechanism — it is a *different* mechanism. `0002` never
changes the duration of the HPD-low pulse; upstream never touches IRQ masking,
the lock loop, the phy retry or the DMA reset. The two are orthogonal and they
**stack**: the code shipped today is upstream's 150 ms hold *and* `0002`'s
sequence, because `7dd27810eea0` is in the base and `0002` applies on top of it
with offsets only.

There is consequently no "replacement" to evaluate. Adopting upstream would not
remove `0002`'s behaviour; it would remove nothing and add nothing.

**One honest caveat about what "working very well" was measured against.**
`7dd27810eea0` first appears in `v7.1.6`. The previous base was `v7.1.5`
([`REBASE-v7.1.5.md`](REBASE-v7.1.5.md)), so the field report that `0002` works
well was almost certainly formed on a kernel **without** the +50 ms hold —
i.e. on `0002` alone. The `v7.1.7` build is the first to carry both. That is an
improvement in the same direction, not a regression risk, but it means the
"both together" configuration has not been separately observed, and it is not
claimed here that it has.

---

## Criterion 2 — upstream review pedigree

Good, and not in dispute — it simply is not a reason to change anything here.

| Signal | Value |
|---|---|
| Revision | `v2` (v1 revised after review) |
| Review feedback incorporated | Sebastian Reichel — subject prefix corrected; `s/sink/source/` fixed in the commit message |
| `Signed-off-by` | Dmitry Osipenko (Collabora) → Hans Verkuil (media maintainer) → Greg Kroah-Hartman (stable) |
| `Fixes:` | `7b59b132ad43` ("media: platform: synopsys: Add support for HDMI input driver") |
| `Cc: stable@vger.kernel.org` | yes — which is exactly why it reached us via `v7.1.6` |
| `Reported-by` | **Ross Cawston** — the author of `0001`–`0005` |
| Independent `Reviewed-by` / `Tested-by` trailers | **none on the posting** |

The `Reported-by` line is worth a second look. Upstream's fix exists *because*
Ross Cawston reported the symptom on 2026-02-09 — the same date `0002` carries.
So the sequence is: he hit the problem, wrote `0002` for his own tree, and
reported it upstream; Collabora answered with the smallest change that fixed
their reproduction. `0002` is not a rejected alternative to `d1162a5adbb5` — it
was never submitted, and the two were authored for different purposes by
different people.

---

## Criterion 3 — clean applicability to the `v7.1.7` base

Tested for real against a clean `git worktree` at `v7.1.7`, using the patch as
published (patchwork mbox for `20260325105742.63236-1-...`), not by reading:

```
$ git apply --check -p1 d1162a5.mbox
error: patch failed: drivers/media/platform/synopsys/hdmirx/snps_hdmirx.c:506
error: drivers/media/platform/synopsys/hdmirx/snps_hdmirx.c: patch does not apply
exit=1

$ git apply --check -R -p1 d1162a5.mbox
exit=0

$ git apply --3way -p1 d1162a5.mbox
Applied patch to 'drivers/media/platform/synopsys/hdmirx/snps_hdmirx.c' cleanly.
$ git diff --stat
                       # ← empty
```

Read those three together:

- **Forward apply fails** because the context line it needs, `msleep(100);`, no
  longer exists in the base.
- **Reverse apply succeeds**, which is only possible if the change is already
  present.
- **Three-way apply produces an empty diff** — the definition of a no-op.

Confirmed directly in the base source, `snps_hdmirx.c:511` at `v7.1.7`:

```c
	/* 100ms delay as per HDMI spec + extra 50ms to cover internal delay */
	if (!en)
		msleep(100 + 50);
```

And `0002` still applies on top, offsets only, unchanged from T7's ledger:

```
$ git apply --check -p1 --verbose patches/0002-rockchip-rk3588-hdmirx-edid-fix-v1.patch
Hunk #2 succeeded at 626 (offset 2 lines).
…
Hunk #8 succeeded at 2219 (offset 48 lines).
exit=0
```

**Prerequisite commits:** not applicable — the candidate has none, being already
merged into this very base.

> Note for the next evaluator: `git am --check` does not exist (`error: unknown
> option 'check'`). The dry-run verb is `git apply --check`; add `-R` for the
> already-applied test and `--3way` for the no-op proof.

---

## Criterion 4 — behaviour on both shipped boards' DT

**Source-verified: identical on both boards, and neither patch has any DT
coupling.** Not board-verified — see the gap statement below.

Both shipped boards declare the HDMI receiver the same way at `v7.1.7`:

| Board | `&hdmi_receiver` |
|---|---|
| `rk3588-rock-5b.dtsi` | `hpd-gpios = <&gpio1 RK_PC6 GPIO_ACTIVE_LOW>; status = "okay";` |
| `rk3588-orangepi-5-plus.dts` | `hpd-gpios = <&gpio1 RK_PC6 GPIO_ACTIVE_LOW>;` + `pinctrl-0/-names`; `status = "okay"` |

The single DT property that could make `hdmirx_hpd_ctrl()` — the only function
upstream changes — behave differently between boards is `hpd-is-active-low`:

```c
	if (!device_property_read_bool(dev, "hpd-is-active-low"))
		hdmirx_dev->hpd_trigger_level_high = true;
```

`grep -rn "hpd-is-active-low" arch/arm64/boot/dts/rockchip/` at `v7.1.7` returns
**nothing** — no Rockchip board in the tree sets it. Both CeraLive boards
therefore take the `hpd_trigger_level_high = true` path, and the +50 ms hold
applies identically to each. `0002` touches no device tree at all, and the
board-side difference between the two DTs (Orange Pi 5+ pinmuxes `hdmim1_rx_*`,
Rock 5B+ inherits its pinctrl) is upstream of the driver logic either patch
changes.

> **Open / deferred — not tested on hardware.** No RK3588 board is reachable from
> this repository, and this repository gates patch application only. Nothing in
> this document was observed on a Rock 5B+ or an Orange Pi 5+ with a real HDMI
> source attached. Every claim above is read out of the `v7.1.7` source tree and
> the published patch. The behavioural question below stays open for whoever gets
> a board.

---

## Criterion 5 — known-defect fixes included

Upstream carries one defect fix, and we already have it:

| Defect | Carried by | In our base? |
|---|---|---|
| EDID change not detected by source/display side, caused by too-short HPD-low hold — `Fixes: 7b59b132ad43` | `d1162a5adbb5` / `7dd27810eea0` | **yes**, since `v7.1.6` |

The whole `synopsys/hdmirx` neighbourhood was swept for anything else the
candidate might have dragged in. Every commit touching `hdmirx` in mainline was
enumerated and checked against the base:

| Mainline commit | Subject | State at `v7.1.7` |
|---|---|---|
| `d1162a5adbb5` | Fix HPD lane hold time | **present** (as `7dd27810eea0`) |
| `2fb0481fe0d7` | support use with sleeping GPIOs | present (`gpiod_get_value_cansleep`) |
| `a813338d910b` | Detect broken interrupt | present (`hdmirx_detect_broken_interrupt()`) |
| `54eff31301a0` | replace `system_unbound_wq` with `system_dfl_wq` | **absent** — base still uses `system_unbound_wq` |

Only `54eff31301a0` is missing, and it is a tree-wide workqueue-API rename with
no defect behind it — not a backport candidate, and deliberately not proposed as
one.

It is, however, worth one forward-looking line: `0002` **adds** a
`queue_delayed_work(system_unbound_wq, …)` call, so it is consistent with the
base today. If a future base absorbs `54eff31301a0`, `0002` will still compile
(`system_unbound_wq` is not removed by that commit) but will be stylistically out
of step with its surroundings. That is a note for the next rebase, not a defect.

`0002` itself carries **no** `Fixes:` tag and no upstream defect reference — it is
an unsubmitted fork patch, and its evidence is field behaviour, not a bug
database.

---

## Revisited 2026-08-08 — 4K60 input capability

**Why this section exists.** After the original evaluation was written, the user
stated that both shipped boards — Rock 5B+ and Orange Pi 5+ — are capable of
**4K@60 HDMI input**, and asked whether that changes the verdict.

**Outcome: the verdict does not change. It is REINFORCED, and materially so** —
but partly for reasons other than the ones proposed, and one part of the proposed
reasoning does not survive checking. Both are set out below, because a revisit
that only confirms what it set out to confirm is not worth reading.

Everything here is read out of the `v7.1.7` tree and the patch files. **No board
was involved.** The hardware-only items are collected in
[§ Requires board validation at 4K60](#requires-board-validation-at-4k60).

### The correction first — EDID reads do not ride the TMDS link

The proposed reasoning was that 4K60's higher TMDS clock leaves *"less margin"*
for hot-plug detection and EDID block reads, so the 150 ms hold might be
insufficient at 4K60. Checked, and **that specific mechanism does not hold**:

- **EDID is read over DDC — an I²C sideband — not over TMDS.** DDC runs at
  standard-mode I²C rates regardless of the video timing that will later be
  carried on the link. A 4K60 EDID does not get read faster or slower because the
  eventual pixel clock is 594 MHz rather than 148.5 MHz.
- **The 150 ms is HPD-*low hold*, not read time.** `hdmirx_hpd_ctrl(dev, false)`
  drives HPD low and sleeps; the source's EDID re-read happens *after* HPD rises
  again. Whatever the read costs, it is spent outside the window the constant
  governs — so a larger EDID does not eat into the hold budget.
- **HDMI's ≥100 ms HPD-low requirement is not resolution-scaled.** It exists so a
  source reliably observes the disconnect edge. Nothing in it varies with the
  timing that follows.

So, as a *hold-time* question, "is 150 ms enough at 4K60" is
**resolution-independent**, and 4K60 neither strengthens nor weakens
`7dd27810eea0`'s constant. Recording this plainly matters: had the revisit
accepted the premise, it would have manufactured an argument the source does not
support, and the conclusion would have been right for a wrong reason.

**The conclusion nonetheless stands, via a different and stronger route.** The
resolution-sensitive stage is not the *hold*, it is the **lock** — and the lock
stage is exactly what `0002` rebuilds. That, plus a capability finding neither
side had, is the rest of this section.

### The finding that changes the weight of the verdict

**The driver's built-in default EDID advertises 4K30, not 4K60.** Decoded directly
out of `edid_default[]` in `snps_hdmirx.c` at `v7.1.7` (2 blocks, 256 bytes,
CTA-861 rev 3 extension):

| Field | Value | Meaning |
|---|---|---|
| Video Data Block SVDs | VIC 95, 94, 93, 16, 31, 4, 19, 34, 33, 32, 5, 20, 2, 17, 1 | 2160p**30**, 2160p25, 2160p24, 1080p60 … — **VIC 97 (2160p60) is absent** |
| HDMI 1.4b VSDB `Max_TMDS_Clock` | `0x3C` → **300 MHz** | covers 4K30's 297 MHz; **below 4K60's 594 MHz** |
| HDMI Forum VSDB `Max_TMDS_Character_Rate` | **0** | no >340 MHz capability declared |
| HDMI Forum VSDB `SCDC_Present` | **0** | **SCDC not offered** |
| HDMI Forum VSDB `LTE_340Mcsc_scramble` | **0** | scrambling below 340 MHz not offered |

The Kconfig help text for `VIDEO_SYNOPSYS_HDMIRX_LOAD_DEFAULT_EDID` says the same
thing in prose — *"exposes display modes up to 4k@30Hz, which have best
compatibility with HDMI transmitters"* — and the bytes confirm it rather than
merely repeating it.

The hardware is not the limit. The driver's `v4l2_dv_timings_cap` allows
`20000000 … 600000000` Hz pixel clock, so 594 MHz is inside the advertised range.

**Therefore: on these boards, 4K60 input is only reachable by writing a custom
EDID at runtime through `VIDIOC_S_EDID` — and that write path is precisely what
`0002` exists to repair.** Its own generated subject says so: *"make a written
EDID visible to the HDMI source"*. At 4K30 an operator can stay on the built-in
EDID and never exercise the path at all; at 4K60 the path is mandatory.

That converts `0002` from *"a fix that is reported to work well"* into *"a
prerequisite for the headline capability of both shipped boards"*. The bar for
replacing it was already high; this raises it further.

### And writing a 4K60 EDID switches on the exact path `0002` hardens

The two halves connect, and the connection is in the register code:

1. A 4K60 EDID must set `SCDC_Present = 1` and a `Max_TMDS_Character_Rate` above
   340 MHz — otherwise a compliant source will not attempt 4K60 at all.
2. Once it does, the source raises the SCDC **TMDS bit-clock ratio** to 1/40 and
   enables scrambling. `hdmirx_tmds_clk_ratio_config()` reads that back from
   `SCDC_REGBANK_STATUS1` (`SCDC_TMDSBITCLKRATIO`) and sets `TMDS_CLOCK_RATIO` in
   `PHY_CONFIG`; its own debug string for that branch is
   *"HDMITX greater than 3.4Gbps"*.
3. **That branch is unreachable with the default EDID** (`SCDC_Present = 0`). It
   only ever executes once someone has written a 4K60-capable EDID — i.e. only on
   the far side of `0002`'s fix.

So the high-ratio PHY path and the EDID-write path are not two independent
concerns that happen to both matter at 4K60. The first is *gated on* the second.

### What the lock loop actually costs — the numbers behind "300 → 600"

The loop's per-iteration cost is not obvious from the diff, so it was measured out
of the source rather than assumed. Each iteration calls `tx_5v_power_present()`:

```c
	for (i = 0; i < 10; i++) {
		usleep_range(1000, 1100);
		val = gpiod_get_value_cansleep(hdmirx_dev->detect_5v_gpio);
		if (val > 0) cnt++;
		if (cnt >= detection_threshold /* 7 */) break;
	}
```

With a cable present that is 7 × ~1 ms ≈ **7 ms per loop iteration**. The four
register reads and `hdmirx_tmds_clk_ratio_config()` are MMIO-only and negligible.

| | base `v7.1.7` | with `0002` |
|---|---|---|
| Loop bound | `for (i = 0; i < 300; i++)` | `for (i = 1; i < 600; i++)` |
| Wall-clock ceiling | ≈ **2.1 s** | ≈ **4.2 s** |
| Lock criterion | **first** sample with all three bits set | `j > 20` → **21 consecutive** good samples |
| Continuous stability required | none — one sample | ≈ **147 ms** |
| PHY recovery during the wait | none | `hdmirx_phy_config()` at `i == 300` |

Three things follow, and all three are 4K60-relevant:

- **A single-sample lock criterion is weakest exactly where the link is hardest.**
  At 594 MHz character rate with scrambling, `TMDSVALID_STABLE_ST`,
  `HDMIRX_LOCK` and `TMDSQPCLK_LOCKED_ST` can all read good on a transient before
  the CDR has genuinely settled. Requiring ~147 ms of *uninterrupted* stability is
  a direct guard against declaring lock on that transient. Nothing in the base or
  in `7dd27810eea0` provides it.
- **`0002`'s PHY retry fires precisely when the unpatched driver would give up.**
  `i % NO_LOCK_CFG_RETRY_TIME` with `NO_LOCK_CFG_RETRY_TIME = 300` triggers once,
  at `i == 300` — the base's exact failure point. The base sets the
  `TMDS_CLOCK_RATIO` bit every iteration but never re-runs `hdmirx_phy_config()`,
  which is the function that asserts `PHY_RESET`. If the PHY latched a
  configuration from before the SCDC ratio flipped — the 4K60 case, and only the
  4K60 case, since the ratio never flips below 340 MHz — bit-poking alone will not
  recover it, and a re-init is the appropriate action. Cost of that retry is two
  `usleep_range(100, 110)` calls, ≈0.2 ms.
- **This is the "does not depend on a fixed timing constant" property, and it is
  real.** `0002` does not replace one constant with a larger constant; it changes
  the *criterion* — retry until stable, with a bounded ceiling — which is what
  degrades gracefully as the link gets harder. The proposed reasoning was right on
  this point, and the numbers above are what make it more than an assertion.

The post-lock change fits the same picture: `0002` adds `hdmirx_reset_dma()` and
lengthens the settle from `msleep(50)` to `msleep(500)` before
`hdmirx_format_change()`. At 4K60 the capture DMA is moving roughly an order of
magnitude more data per second than at 1080p60, and the in-tree CMA comment sizes
the pool from 4K frames (below). A longer, reset-qualified settle is the
conservative choice at that data rate. **Not quantified here** — no measurement of
actual settle time exists without a board.

### Criteria 3 and 4, re-checked against 4K60

**Criterion 3 — applicability.** Unchanged, and 4K60 does not bear on it. The
upstream counterpart is still already in the base and still applies as a no-op;
that is a property of the tree, not of the video mode. `0002` still applies with
offsets only.

**EDID extension blocks are not a constraint, and `0002` does not interact with
their size.**

| Fact | Value at `v7.1.7` | Consequence for 4K60 |
|---|---|---|
| `EDID_NUM_BLOCKS_MAX` | `4` (512 bytes) | a 4K60 EDID is typically 2 blocks / 256 bytes — fits with 2 blocks of headroom |
| `S_EDID` clamp | `if (edid->blocks > EDID_NUM_BLOCKS_MAX) edid->blocks = EDID_NUM_BLOCKS_MAX;` | oversized writes are clamped, not rejected — pre-existing behaviour, untouched by `0002` |
| `0002`'s IRQ-masked window | wraps `hdmirx_plugout()` + `hdmirx_write_edid()` | scales with block count only through the register-write loop in `hdmirx_write_edid_data()` — sub-millisecond class; a 2-block 4K60 EDID is not a meaningful widening |

`0002` adds no block-count logic, no per-block sequencing, and no CTA-861 parsing.
It is agnostic to what is in the EDID; it fixes *when and how* the write is made
visible. So the answer to "does its plugout/DMA-reset logic interact with CEA-861
extension blocks?" is **no** — and that is a finding, not an omission.

**Criterion 4 — both boards, re-checked for 4K provisioning.** Still identical
across the two boards, and both are provisioned for 4K:

| | Rock 5B+ | Orange Pi 5+ |
|---|---|---|
| `&hdmi_receiver` | `okay`, `hpd-gpios = <&gpio1 RK_PC6 GPIO_ACTIVE_LOW>` | same, plus `hdmim1_rx_*` pinctrl |
| `hpd-is-active-low` | not set (no Rockchip board sets it) | not set |
| `&hdmi_receiver_cma` | **`okay`** — via `rk3588-rock-5b-plus.dts` → `rk3588-rock-5b.dtsi` → `rk3588-rock-5b-5bp-5t.dtsi:227` | **`okay`** — directly in `rk3588-orangepi-5-plus.dts:163` |

> **A wrong suspicion, recorded rather than quietly dropped.** `rk3588-rock-5b.dtsi`
> contains no `&hdmi_receiver_cma` node, which looked like a board asymmetry — one
> board with a dedicated 4K CMA pool and one falling back to the default CMA via
> the driver's `"no reserved memory for HDMIRX, use default CMA"` warning path.
> Following the include chain disproved it: the Rock 5B+ enables the pool one level
> up, in `rk3588-rock-5b-5bp-5t.dtsi`. **There is no asymmetry.** Chasing the
> include chain rather than grepping one file is what settled it.

The pool is sized in-tree from 4K frames, and the reasoning is in the DT comment:

```
 * The 4k HDMI capture controller works only with 32bit
 * phys addresses and doesn't support IOMMU. HDMI RX CMA
 * must be reserved below 4GB.
 * The size of 160MB was determined as follows:
 * (3840 * 2160 pixels) * (4 bytes/pixel) * (2 frames/buffer) / 10^6 = 66MB
 * To ensure sufficient support for practical use-cases,
 * we doubled the 66MB value.
```

160 MiB for a 66 MB two-frame 4K working set. That is mainline's sizing, not
ours, and neither `0002` nor the upstream fix touches it. Whether it is enough
headroom at 4K60 with a real vb2 queue depth is a board question, listed below.

### Does this change the verdict? No — it reinforces it

Tested against the possibility that it flips to ADOPT, because the instruction was
to follow the evidence rather than the expectation:

| Could 4K60 make the upstream fix preferable? | Finding |
|---|---|
| Is upstream's fix *more* correct at 4K60? | No. It is 2 lines of HPD-low hold, resolution-independent, and **already in the base** — keeping `0002` does not forgo it. Both are in the shipped build. |
| Does `0002` do anything *harmful* at 4K60? | Nothing found in source. Its changes lengthen and qualify a wait, add a PHY re-init, and mask IRQs across an EDID write. The IRQ-masked window is bounded by the write loop and does not scale with pixel clock. |
| Does 4K60 expose a gap in `0002` that upstream fills? | No. Upstream touches only `hdmirx_hpd_ctrl()`'s body, which `0002` never modifies. There is no gap for it to fill. |
| Is there a *third* option 4K60 argues for? | Not from these sources. `54eff31301a0` is a workqueue rename; no other mainline `hdmirx` commit addresses 4K60 lock or EDID. |

**The verdict is unchanged: KEEP `0002` — now held more firmly.** Before this
revisit the case was "there is nothing to adopt". It is now additionally "`0002`
is on the critical path for 4K60, which is a capability both shipped boards are
specified for, and its retry-and-qualify lock criterion is the property that
matters most at the point where the link is hardest."

### Requires board validation at 4K60

**These items have since moved.** They now live in
[`BOARD-QUALIFICATION.md`](BOARD-QUALIFICATION.md) § 9, as unticked checklist legs
with the same B1–B7 numbering; that file is the executable copy. The table below is
kept as the record of where they came from and why each one is hardware-only —
none can be settled by reading source, and none is claimed to have been. **Tick
legs in `BOARD-QUALIFICATION.md`, never here.**

| # | Check | Why it cannot be answered here |
|---|---|---|
| B1 | Write a 4K60-capable EDID (`SCDC_Present = 1`, `Max_TMDS_Character_Rate ≥ 594 MHz`, VIC 97) via `VIDIOC_S_EDID` and confirm the **source actually re-reads it** and offers 2160p60 | Needs a real HDMI source that re-reads on HPD and honours SCDC |
| B2 | Confirm the SCDC bit-clock ratio flips to 1/40 and the receiver **locks at 594 MHz** — capture `signal lock ok, i:%d` at `debug=1` and record the iteration count | The lock path is register/PHY behaviour; `i` is the only direct evidence and it only exists at runtime |
| B3 | Is the ≈147 ms consecutive-stability requirement **right** at 4K60 — sufficient to reject transients, and not so strict it rejects a genuinely locked link? | Requires observing real lock-bit behaviour during 4K60 negotiation |
| B4 | Is the ≈4.2 s ceiling **enough** at 4K60, and does the `i == 300` PHY re-init actually recover a PHY that latched the pre-flip ratio? | Requires forcing the failure case on hardware |
| B5 | **The original open question, now sharpened to 4K60:** with the 150 ms hold in the base, is `0002`'s sequence still required for a 4K60 EDID to be re-read? | This is the retirement precondition for `0002`. Do not answer it from source |
| B6 | Does 160 MiB of `hdmi_receiver_cma` hold up at 4K60 with a realistic vb2 queue depth, on **both** boards? | Allocation behaviour under load; the DT comment's 66 MB is a two-frame figure |
| B7 | Does `0002`'s `msleep(500)` post-DMA-reset settle need to be that long at 4K60 — or is it over-conservative? | Only measurable against a real link |

Until B5 is answered on a board, **`0002` is not a retirement candidate**, and the
standing instruction quoted at the top of this document says the same thing from
the other direction.

---

## Verdict

> **KEEP `0002`. Adoption is not merely rejected — it is impossible: the upstream
> counterpart is already in the base and applies as a no-op.**
>
> **Revisited 2026-08-08 for 4K60 input capability — unchanged and reinforced.**
> `0002` is a functional prerequisite for 4K60 on both shipped boards: the driver's
> built-in EDID caps at 4K30 with `SCDC_Present = 0`, so 4K60 requires a custom
> EDID written at runtime — the exact path `0002` fixes. See
> [§ Revisited](#revisited-2026-08-08--4k60-input-capability).

Point by point against the bar the user set:

1. **Strictly better?** No. The candidate is not a competing implementation of
   `0002`'s mechanism; it is an orthogonal two-line delay change that we already
   ship. It replaces nothing.
2. **Cleanly applicable?** Moot, and demonstrably so — forward apply fails,
   reverse apply succeeds, three-way apply yields an empty diff.
3. **The standing instruction** — *"in-house is already working very well"* —
   would have required a strictly-better candidate to displace `0002`. No such
   candidate exists. The bar was never approached, let alone cleared.

**Series impact: none.** No file moves to `retired/`, no entry is added to
`backports/`, `patches/` is not regenerated for this evaluation, and
`retired/REGISTRY.md` stays empty. The repository gate was re-run afterwards
regardless, to prove this evaluation changed nothing it should not have.

### What stays open

The one question this evaluation does **not** answer is the one T7 ledgered, and
it is unchanged by the disambiguation:

> With `7dd27810eea0` in the base, is `0002`'s plugout / IRQ-masking / lock-loop /
> DMA-reset sequence still required for a source to re-read a written EDID, or is
> the 150 ms hold now sufficient on its own?

Knowing that the +50 ms hold is the *only* upstream answer — rather than one of
two — narrows the question but does not settle it. Settling it needs an RK3588
board and a real HDMI source. Until then `0002` stays, which is also what the
standing instruction requires. Do not retire it on the strength of a source
reading.

**The 2026-08-08 revisit sharpened this question rather than answering it.** It is
item **B5** in
[§ Requires board validation at 4K60](#requires-board-validation-at-4k60), where it
now reads specifically against a 4K60 EDID — the case that actually matters,
because 4K60 is the only mode on these boards that cannot use the built-in EDID at
all. Six further hardware-only checks (B1–B4, B6, B7) sit alongside it.
All seven now live in
[`docs/BOARD-QUALIFICATION.md`](BOARD-QUALIFICATION.md) § 9, which is where they
get ticked; the table above is their origin record, not the live checklist.

---

## Policy — writing an EDID while a stream is active

Added 2026-08-10 (Wave 6). This is a POLICY statement, not a finding: it records
what the series guarantees about `VIDIOC_S_EDID` during capture, and — more
usefully — what it does not.

**The rule: do not write an EDID while a capture stream is running. Stop the
stream, write the EDID, let the source renegotiate, then start the stream.**

This is not a limitation `0002` introduced; it is what `0002` makes *visible*.
Writing an EDID is not a metadata update — the driver's own sequence deliberately
tears the link down so the source is forced to re-read it:

- `hdmirx_write_edid()` drops HPD, masks the receiver's interrupts, writes the
  new block and re-asserts HPD. The source treats that as an unplug/replug and
  restarts capability negotiation from scratch.
- A renegotiation legitimately changes the resolution, the pixel format and the
  audio sample rate. Buffers already queued to the vb2 queue were sized for the
  PREVIOUS format.
- Patch `0003` exists precisely because that replug path used to overflow a
  buffer, and patch `0005`'s audio worker re-derives its sample rate from the
  ACR packets of whatever the source now sends.

So an EDID write during an active stream is a deliberate mid-stream format
change with no format-change handshake. The honest outcomes are a `vb2` queue
error, a stalled `DQBUF`, or a stream that continues at a resolution the source
is no longer sending — none of which the driver can prevent, because the source,
not the driver, decides what to send after a replug.

**What the series DOES guarantee**, and these are the three patches that make
the stop/write/start sequence safe rather than merely conventional:

1. `0002` — a written EDID is actually visible to the source. Without it the
   source re-reads the block it already had, so the write appears to succeed and
   changes nothing.
2. `0003` — the replug the write triggers does not overflow the capture buffer,
   and a stream that was running when the link dropped gets a `vb2` queue error
   rather than a `DQBUF` that hangs until userspace times out.
3. `0017` — the audio worker is disarmed and drained across that transition
   rather than left polling a receiver whose HPD is down, and a sample-rate
   change the audio clock refuses is reported instead of being recorded as
   though it had taken.

**What is deliberately NOT done.** The driver does not reject `VIDIOC_S_EDID`
while streaming. Two reasons: the V4L2 API does not define that refusal for this
ioctl, so returning `-EBUSY` would be a driver-specific behaviour userspace
cannot portably expect; and a userspace that genuinely wants to renegotiate
mid-session has no other mechanism. The constraint is therefore documented and
owned by the caller — CeraUI stops the capture pipeline before an EDID change —
rather than enforced with an invented error.

**Board validation status: NOT RUN.** No board check in
[`BOARD-QUALIFICATION.md`](BOARD-QUALIFICATION.md) § 9 currently writes an EDID
while streaming, and none should be added that expects it to work. The check
worth adding is the opposite one: prove that stop → write → renegotiate → start
produces a stream at the new format, and that the audio card follows it.
