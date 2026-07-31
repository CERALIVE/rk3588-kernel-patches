# Rebase ledger — upstream `v6.19-rc8` → CeraLive target `v7.1.5`

Upstream developed and tested this series against `v6.19-rc8` (its own
`README.MD` says so). CeraLive targets the Armbian rk3588 **edge** kernel, which
resolves to `7.1` — see [`kernel-pin.env`](../kernel-pin.env) and
[`PREFLIGHT.md`](PREFLIGHT.md) for how that was derived.

Mainline moved in between. This document is the hunk-by-hunk record of what
drifted, what we did about it, and — importantly — what we deliberately did
**not** decide.

## The rule this document exists to enforce

> A conflict may be resolved here **only** if the resolution changes how a patch
> *applies*, never what it *does*. Anything requiring a judgement about driver
> behaviour is written down and stopped, not guessed at.

That rule is enforced by three mechanisms, not by good intentions:

1. `rebase/v7.1.5.rules` can only express context edits. `scripts/build-series.py`
   raises if a rule's anchor resolves to a `+` or `-` line, or if it is ambiguous.
2. `scripts/verify-payload-parity.py` compares the ordered set of `+`/`-` lines in
   `patches/` against `upstream/` and requires byte equality.
3. Both run in CI on every push and pull request, and in `scripts/apply.sh` before
   it will apply anything.

---

## Summary

| Patch | Hunks | Clean at `v7.1.5` | Action |
|-------|-------|-------------------|--------|
| `0001` vepu580 encoder | 15 across 13 files | 14 of 15 | 1 context re-anchor (**R1**) |
| `0002` hdmirx EDID | 8, one file | 8 of 8 (offsets only) | none |
| `0003` hdmirx plugout | 2, one file | 2 of 2 (offsets only) | none |
| `0005` hdmirx audio | 8 across 3 files | 7 of 8 | 1 context re-anchor (**R2**) |
| **Stopped for behavioural judgement** | — | — | **none** |

Result: `git am` applies all four patches to `v7.1.5` with exit 0. Transcript in
[§ Verification](#verification).

---

## R1 — `0001`, `rk3588-base.dtsi`, hunk `@@ -1351,6 +1353,92 @@`

**Symptom**

```
error: while searching for:
		clock-names = "aclk", "iface";
		power-domains = <&power RK3588_PD_VDPU>;
		#iommu-cells = <0>;
	};

	av1d: video-codec@fdc70000 {

error: patch failed: arch/arm64/boot/dts/rockchip/rk3588-base.dtsi:1351
```

**What the hunk does.** It inserts six new device-tree nodes — `mpp_srv`,
`rkvenc_ccu`, `rkvenc0`, `rkvenc0_mmu`, `rkvenc1`, `rkvenc1_mmu` — immediately
before the existing `av1d` node. It is pure insertion: 86 added lines, zero
removed lines.

**Why it stopped applying.** The hunk's leading anchor is the closing three lines
of the **neighbouring** `vdec1_mmu` node, which the patch never modifies. Between
`v6.19-rc8` and `v7.1.5`, mainline re-pointed that node from the shared VDPU power
domain to its own:

```diff
-		power-domains = <&power RK3588_PD_VDPU>;
+		power-domains = <&power RK3588_PD_RKVDEC1>;
```

The anchor text changed, so the hunk lost its position. Nothing about the encoder
work is involved.

**Why this is anchor drift and not a behavioural conflict.** Four checks, all run
against `v7.1.5`:

1. Nothing the hunk **adds** mentions `RK3588_PD_VDPU`. The added `rkvenc*` nodes
   use `RK3588_PD_VENC0` / `RK3588_PD_VENC1`.
2. Every dt-binding symbol the added nodes reference still exists:
   `RK3588_PD_VENC0`, `RK3588_PD_VENC1` (`include/dt-bindings/power/rk3588-power.h`);
   `ACLK_RKVENC0/1`, `HCLK_RKVENC0/1`, `CLK_RKVENC0/1_CORE`
   (`include/dt-bindings/clock/rockchip,rk3588-cru.h`);
   `SRST_A_RKVENC0/1`, `SRST_H_RKVENC0/1`, `SRST_RKVENC0/1_CORE`
   (`include/dt-bindings/reset/rockchip,rk3588-cru.h`).
3. No collision: `v7.1.5` defines no `rkvenc0:` / `rkvenc1:` node in
   `rk3588-base.dtsi` (only unrelated `qos_rkvenc*` nodes), and has no
   `drivers/media/platform/rockchip/rkvenc/` directory.
4. After applying, `vdec1_mmu` still reads `power-domains = <&power RK3588_PD_RKVDEC1>` —
   i.e. mainline's current value survived; we did not overwrite it with the stale one.

**Resolution.** One `replace` rule updating the context line to mainline's current
text. Zero added or removed lines change.

---

## R2 — `0005`, `snps_hdmirx.c`, hunk `@@ -135,7 +148,13 @@`

**Symptom**

```
error: while searching for:
	struct gpio_desc *detect_5v_gpio;
	struct delayed_work delayed_work_hotplug;
	struct delayed_work delayed_work_res_change;
	struct hdmirx_cec *cec;
	struct mutex stream_lock; /* to lock video stream capture */
	struct mutex work_lock; /* to lock the critical section of hotplug event */
	struct reset_control_bulk_data resets[HDMIRX_NUM_RST];

error: patch failed: drivers/media/platform/synopsys/hdmirx/snps_hdmirx.c:135
```

**What the hunk does.** Adds six members to `struct snps_hdmirx_dev`:
`delayed_work_audio` before `cec`, then `audio_state`, `codec_dev`, `plugged_cb`,
`aud_clk`, `audio_present` after it.

**Why it stopped applying.** Mainline added a member in exactly the gap the hunk
anchors on:

```c
	struct hdmirx_cec *cec;
	struct mutex phy_rw_lock; /* to protect phy r/w configuration */   /* new in mainline */
	struct mutex stream_lock; /* to lock video stream capture */
```

**Resolution.** One `insert-before` rule that reintroduces `phy_rw_lock` as a
context line ahead of `stream_lock`, and widens the hunk's old/new counts by one.
Zero added or removed lines change.

### The one placement decision, stated openly

Re-anchoring forces a choice: do the patch's new members go **before** or
**after** mainline's `phy_rw_lock`? We kept them where the patch put them —
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
to an equally correct driver. We chose the one that preserves the patch author's
stated intent ("these go right after `cec`") and keeps the rule to a single-line
insertion.

This is recorded here rather than left implicit precisely because it is the only
point in the whole rebase where more than one correct answer existed.

---

## Stopped for behavioural judgement

**None.** Both conflicts were context-anchor drift.

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

---

## Verification

Reproduce with `scripts/apply.sh` — the same script CI runs. Recorded run,
2026-07-31:

```
== Verifying patches/ is generated, not hand-edited
patches/ is in sync (5 files).

== Verifying the series changes nothing upstream/ did not already change
OK   0001-rockchip-rk3588-vepu580-encoder-support-v3.patch: 4414 payload lines identical, dropped 8 .DS_Store stanza(s)
OK   0002-rockchip-rk3588-hdmirx-edid-fix-v1.patch: 41 payload lines identical
OK   0003-rockchip-rk3588-hdmirx-plugout-fix-v1.patch: 13 payload lines identical, dropped 1 .DS_Store stanza(s)
OK   0005-rockchip-rk3588-hdmirx-audio.patch: 455 payload lines identical

all 4 patches: payload byte-identical to upstream.

== Kernel tree at v7.1.5 (155b42bec9cbb6b8cdc47dd9bd09503a81fbe493)

== Applying 4 patches with git am
Applying: rockchip: rk3588: add VEPU580 (RKVENC v2) H.265/H.264/JPEG encoder support
Applying: media: synopsys: hdmirx: make a written EDID visible to the HDMI source
Applying: media: synopsys: hdmirx: fix buffer overflow on repeated HDMI-RX replug
Applying: media: synopsys: hdmirx: add HDMI-RX audio capture support

== Applied cleanly
 arch/arm64/boot/dts/rockchip/rk3588-base.dtsi      |   88 ++
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
 16 files changed, 4917 insertions(+), 6 deletions(-)

== OK — series applies to v7.1.5
```

---

## When the pin moves

Bumping `KERNEL_TAG` in `kernel-pin.env` is the *only* supported way to retarget.
The procedure:

1. Re-run `scripts/preflight.sh` to confirm Armbian still maps rk3588 `edge` to
   the kernel line you expect. Do not assume it does.
2. Update `KERNEL_TAG`, `KERNEL_TAG_OBJECT`, and `KERNEL_COMMIT` together.
3. Create `rebase/<new-tag>.rules`, seeded from the old one. Rules are per-tag on
   purpose — a rule that was right for `v7.1.5` may be wrong for the next tag.
4. Run `scripts/apply.sh`. For every conflict, decide *once*: context drift (rule)
   or behavioural (stop, and write it up in a new `docs/REBASE-<tag>.md`).
5. `scripts/build-series.py && scripts/verify-payload-parity.py` must both pass
   before the change is proposed.
