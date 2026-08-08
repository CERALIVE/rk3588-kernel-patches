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
| Base | `v7.1.7` (`kernel-pin.env`) |
| In-house patch | [`upstream/0002-rockchip-rk3588-hdmirx-edid-fix-v1.patch`](../upstream/0002-rockchip-rk3588-hdmirx-edid-fix-v1.patch) — Ross Cawston, 2026-02-09 |
| Upstream counterpart | `d1162a5adbb5e95953d460b5bde3a04cd4473fe9`, first release `v7.2-rc1` |
| Its stable backport | `7dd27810eea05554d9b43f74022bee9b37a86ac4`, first tag `v7.1.6` — **already in the base** |
| Series change | **none** — `patches/` untouched, `retired/` untouched |

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

## Verdict

> **KEEP `0002`. Adoption is not merely rejected — it is impossible: the upstream
> counterpart is already in the base and applies as a no-op.**

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
