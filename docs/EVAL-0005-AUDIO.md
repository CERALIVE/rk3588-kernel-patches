# Evaluation — `0005`+`0006` HDMI-RX audio vs the upstream "HDMI Input Audio" PATCHv4

**Verdict: KEEP `0005` and `0006`. Do not adopt PATCHv4 — yet.**

Unlike [`EVAL-0002-EDID.md`](EVAL-0002-EDID.md), this candidate is *real*. It is a
four-patch series, cleanly applicable to our base, carrying `Reviewed-by` from
three maintainers and a `Tested-by`. It is nonetheless declined, for two reasons
that are independent of each other:

1. It is **not strictly better** — it is *differently* better. It fixes four
   things `0005` gets wrong and drops six things `0005` gets right, including
   multichannel audio, jack reporting and cable-pull teardown.
2. Its device-tree half **enables the sound card on Orange Pi 5 Plus only**. Our
   other shipped board, Rock 5B+, would be left with a bound codec and no ALSA
   card — the precise regression that `image-building-pipeline`'s own KEY FACT
   was written to prevent.

| | |
|---|---|
| Evaluated | 2026-08-08 |
| Base | `v7.1.7` (`kernel-pin.env`) — tag object `c8fde2689e91a16e9d4b11fe3b08e45c89870585`, commit `c7ba9d6de43e9d9bd755b1f3c19501a38898c6b6` |
| In-house patches | [`upstream/0005-rockchip-rk3588-hdmirx-audio.patch`](../upstream/0005-rockchip-rk3588-hdmirx-audio.patch) (Ross Cawston) + [`ceralive/0006-rk3588-hdmirx-audio-sound-card.patch`](../ceralive/0006-rk3588-hdmirx-audio-sound-card.patch) (first-party) |
| Upstream candidate | `[PATCH v4 0/4] media: synopsys: hdmirx: add HDMI audio capture support`, Igor Paunovic, 2026-07-21 — <https://lore.kernel.org/r/20260721064115.64809-1-royalnet026@gmail.com> |
| Its upstream status | `sent-v4` — fully reviewed, **not merged**, author pinged for pickup 2026-08-05 |
| Series change | **none** — `patches/` untouched, `retired/` untouched, `backports/` untouched |

---

## The standing instruction this evaluation was held to

The user's instruction, quoted verbatim:

> **"in-house is already working very well"**

That sets the bar: a replacement must be **strictly better**, not merely also
correct and not merely more upstream-shaped. This candidate is the first one in
this repository to get close enough that the bar had to actually be applied
rather than merely stated. It does not clear it.

---

## What the candidate actually is

The Collabora status table's row reads "HDMI Input – Audio". Following T10's
lesson — *never treat a status-table label as the patch's identity* — the
Message-ID was resolved against the archive itself. `patchwork.kernel.org`'s API
returns **zero** results for this Message-ID (it is a `linux-media` posting that
patchwork did not index), so the thread was read from
`https://lore.kernel.org/all/<msgid>/t.mbox.gz`, which is not behind the Anubis
gate that blocks the HTML views and the `/raw` endpoint.

34 archived messages, 4 patches, 3 human reviewers, 1 bot:

| # | Subject | Files |
|---|---|---|
| 1/4 | `dt-bindings: media: snps,dw-hdmi-rx: add #sound-dai-cells` | `Documentation/devicetree/bindings/media/snps,dw-hdmi-rx.yaml` |
| 2/4 | `media: synopsys: hdmirx: add HDMI audio capture support` | `snps_hdmirx.c` (+306), `snps_hdmirx.h` (+8) |
| 3/4 | `arm64: dts: rockchip: add HDMI RX audio on RK3588` | `rk3588-extra.dtsi` (+18) |
| 4/4 | `arm64: dts: rockchip: enable HDMI RX audio capture on Orange Pi 5 Plus` | `rk3588-orangepi-5-plus.dts` (+8) |

So the series is the **same shape as ours**: a driver patch that registers the
ASoC codec, plus device-tree patches that turn it into an ALSA card. That is the
whole reason criterion 6 exists — patches 3/4 and 4/4 are a direct competitor to
`0006`, not a complement to it.

---

## Criterion 1 — mechanism and coverage delta

Both implementations do the same core thing, and they do it the same way: register
the generic `hdmi-audio-codec` platform device as a child of `snps_hdmirx`, recover
the sample rate from the ACR N/CTS values against the measured TMDS character rate,
and run a periodic worker that nudges the audio reference clock in ppm steps to
hold the audio FIFO fill level near `INIT_FIFO_STATE * 4`. The ppm ladder
(`10 / +20 / +200`, thresholds `16 / 32 / 100 / 200`), the FIFO thresholds
(`0x20`/`0x160` pass, `0x8`/`0x178` mute) and the supported-rate table are
byte-for-byte the same in both. Both descend from the same Rockchip BSP code.

The differences are entirely in what is built **around** that shared core.

### Where upstream v4 is better

| # | Upstream v4 | In-house `0005` |
|---|---|---|
| 1 | **System suspend/resume.** `hdmirx_suspend()` cancels the audio worker before the controller clocks are gated; `hdmirx_resume()` re-programs the audio path from `audio_fs` and re-arms the worker if a capture stream is live | **Nothing.** `hdmirx_suspend()` is untouched; the worker keeps firing and reading `AUDIO_FIFO_STATUS2` on a gated bus. Verified: `awk '/hdmirx_suspend\|hdmirx_resume/,/^}/' … \| grep -c delayed_work_audio` → **0** |
| 2 | **Capture-only card.** `.no_i2s_playback = 1, .no_spdif_playback = 1` | Registers playback DAIs on a receiver that cannot play. `codec_data` is `{ .spdif = 1, .i2s = 1, .max_i2s_channels = 8 }` — no direction flags |
| 3 | **S/PDIF honestly refused.** `hw_params()` returns `-EOPNOTSUPP` for `HDMI_SPDIF` | `hw_params()` returns `0` unconditionally, so an S/PDIF open would silently succeed and produce nothing. Unreachable from our DT (`#sound-dai-cells = <0>` cannot address DAI 1), but the code is wrong |
| 4 | **Worker is stream-scoped.** Armed in `hw_params()`, cancelled in `audio_shutdown()` — no register traffic while idle | Worker starts at plug-in and runs forever at 200 ms–1 s while a cable is attached, whether or not anything is capturing |
| 5 | **Documented, accepted DT binding** for `#sound-dai-cells` | No binding. `0006` adds `#sound-dai-cells = <0>` to a node whose schema (`additionalProperties: false`) does not permit it — a `dtbs_check` violation we simply do not run |
| 6 | Card named `"RK3588 HDMI-IN"` — the string ALSA UCM matches on | Card named `"hdmirx"` |

### Where in-house `0005` is better

All six verified by symbol count against a tree with upstream v4 actually applied:

| # | In-house `0005` | Upstream v4 | Evidence |
|---|---|---|---|
| 1 | **Channel-count detection.** Reads the Audio InfoFrame (`PKTDEC_AUDIF_PB3_0`) each worker tick and, for >2 channels, sets `SPEAKER_ALLOC_OVR_EN` and writes `AUDIO_PROC_CONFIG3 = 0xffffffff` | **Absent entirely.** Multichannel (5.1 / 7.1) HDMI input is not handled | `hdmirx_audio_ch` → 0 hits · `AUDIO_PROC_CONFIG3` → 0 hits · `PKTDEC_AUDIF` → 0 hits |
| 2 | **Jack / plug reporting.** Implements `hook_plugged_cb`, stores `plugged_cb` + `codec_dev`, and drives audio-present transitions into the ASoC jack | **Absent entirely** — and Dmitry Osipenko named this as required future work in his review | `plugged_cb` → 0 · `hook_plugged_cb` → 0 · `audio_present` → 0 |
| 3 | **Cable-pull teardown.** `hdmirx_plugout()` reports unplug, cancels the audio work and clears `audio_present` | `hdmirx_plugout()` is **not touched** by the audio patch. On a cable pull the worker keeps polling and no state is invalidated | `hdmirx_plugout` body read out of the adopted tree — contains no audio call |
| 4 | **Pre-locked before capture opens.** `hdmirx_audio_set_state(dev, true)` starts the worker at plug-in and on resolution change, so the clock is already tracking when an app opens the PCM | Worker starts only at `hw_params()`, so the first stretch of every capture runs pre-lock | `grep -n audio_work` → armed only at `hw_params` and `resume` |
| 5 | **Self-contained Kconfig.** `select SND_SOC_HDMI_CODEC` in `hdmirx/Kconfig` | **No Kconfig change at all.** The codec driver has to arrive from somewhere else | `v7.1.7` `hdmirx/Kconfig` has no such select; upstream 2/4 touches only `.c`/`.h` |
| 6 | **Rate-validity gate.** `is_validfs()` rejects an unrecognised rate and backs the worker off to 1 s | No validity gate; falls back to `hparms->sample_rate`, then to a hard-coded `48000` | `is_validfs` → 0 hits |

Point 5 deserves one honest qualification rather than an alarm. `SND_SOC_HDMI_CODEC`
is `select`ed by `drivers/gpu/drm/bridge/synopsys/Kconfig` (`DRM_DW_HDMI`) and by
three entries in `sound/soc/rockchip/Kconfig`, so on a realistic RK3588 config it
is almost certainly already enabled — the HDMI **transmitters** pull it in. The
delta is therefore about robustness, not a predicted breakage: `0005` states its
own dependency, upstream v4 inherits it from an unrelated subsystem.

### Net

Not a subset relationship in either direction. Upstream v4 is the better-behaved
*kernel citizen*; `0005` is the better-behaved *appliance*. For a device whose
entire job is to capture whatever HDMI source an operator plugs in — including
multichannel sources, including mid-stream cable pulls — losing items 1–4 above
to gain suspend support on a box that never suspends is not an upgrade.

**"Strictly better" is not met.**

---

## Criterion 2 — upstream review pedigree

Strong. This is the finding that made the evaluation non-trivial, and it is
recorded in full rather than summarised, because "PATCHv4" alone says nothing.

| Patch | Trailers earned on the v4 posting |
|---|---|
| 1/4 dt-bindings | `Reviewed-by:` Sebastian Reichel (Collabora) · `Reviewed-by:` **Krzysztof Kozlowski** (DT binding maintainer) · `Reviewed-by:` Dmitry Osipenko (Collabora) |
| 2/4 driver | `Reviewed-by:` **and** `Tested-by:` Dmitry Osipenko |
| 3/4 SoC dtsi | `Reviewed-by:` Sebastian Reichel · `Reviewed-by:` Dmitry Osipenko |
| 4/4 board dts | `Reviewed-by:` Sebastian Reichel · `Reviewed-by:` Dmitry Osipenko |

Four revisions of genuine iteration: v1 (RFC) → v2 (Sebastian: register the S/PDIF
DAI so indexes match the binding; Dmitry: use `platform_device_register_data()`,
drop the fixed 32-bit DMA mask; look the `audio` clock up by name instead of
indexing `clks[1]`) → v3 (Dmitry: restore the v1 teardown; drop the `get_dai_id`
stub) → v4 (Dmitry: support system suspend instead of an `-EBUSY` guard;
Krzysztof: `$ref` `dai-common.yaml` + `unevaluatedProperties`; Sebastian: move the
whole card into `rk3588-extra.dtsi` as a shared disabled node).

**But it is not merged.** No maintainer has picked it up. On **2026-08-05** the
author pinged Dmitry and Mauro: *"all four patches carry Reviewed-by tags (2/4 also
has Dmitry's Tested-by) and no changes have been requested since 23 July. Is there
anything needed from my side for the series to be picked up into the media tree?"*
As of this evaluation (**2026-08-08**) that ping is unanswered in the archive.

### The reviewers' own reservations, recorded

Two are named by the participants themselves and neither is resolved:

- **Dmitry Osipenko, on 2/4, alongside his `Reviewed-by`:** *"Current variant of
  audio support requires userspace to manually select appropriate audio freq on
  capture. This needs to be improved later on for regular userspace apps by
  dynamically registering audio CODEC on HDMI cable plug event and reading out
  actual audio freq on the wire, restricting the CODEC's rate, which might require
  extension of the `hdmi_codec_ops`."* — i.e. the reviewer is telling us the plug-event
  and rate-restriction work is still missing. `0005` already carries the plug-event
  half of exactly that (criterion 1, item 2).
- **The author, in the v4 cover letter:** *"a second suspend/resume cycle in the
  same boot can leave the audio datapath silent until reboot… under investigation
  as a follow-up."* The one capability upstream has and we lack is itself shipped
  with a known open defect.

### The bot findings, and why they are not disqualifying

`sashiko-bot@kernel.org` filed three items. They are recorded because the task
requires the actual review status, not a flattering summary:

| Finding | Severity | Status |
|---|---|---|
| `swab32()` on the ACR word "scrambles" N/CTS | High, *new* | **Rebutted by the author**, third time raised. Per the HDMI spec, CTS is stored MSB-first (`CTS[19:16]` in PB1[3:0], `[15:8]` in PB2, `[7:0]` in PB3), so byte-reversing the word is what lines it up. Empirically settled: a 44.1 kHz source is *detected* as 44.1 kHz, not defaulted to 48 kHz. Dmitry's `Tested-by` landed after this exchange. **Our `0005` reaches the identical value by explicit shift-and-mask instead of `swab32()` — the two are arithmetically the same operation.** |
| `video_device` UAF on unbind with an open fd | High, *pre-existing* | Real-looking and **not this series' bug**. Dmitry: *"No need to worry about it for this series."* Applies to our base as much as to the candidate |
| hdmi-codec's `SND_SOC_DAPM_OUTPUT("RX")` widget is a sink, not a source, so DAPM may not power the capture path | High, *pre-existing* | Unanswered in the thread. Applies to `hdmi-codec` generally — **so it applies to `0005` too**, which uses the same codec. Not a discriminator either way, but worth knowing that our working card works *despite* it |

**Pedigree verdict: excellent for an unmerged series, and unmerged is still
unmerged.** Importing it now means carrying a fork of a moving target: if v5
arrives with maintainer-requested changes, our `backports/` copy is instantly
stale and its `commit <sha> upstream.` provenance line cannot be filled in,
because there is no SHA.

---

## Criterion 3 — clean applicability to the `v7.1.7` base

**PASS.** This is where the candidate genuinely beats T10's: it applies, for real,
with no fuzz. Tested in a throwaway `git worktree` off the pinned tree, per the
T10 procedure.

### Step 0 — is any of it already in the base?

Content check on the audio path across the whole `synopsys/hdmirx` directory at
`v7.1.7`:

```
hdmirx_audio_startup     0 hits
plugged_cb               0 hits
HDMI_CODEC_DRV_NAME      0 hits
sound/hdmi-codec.h       0 hits
AUDIO_ENABLE             0 hits
hdmirx_audio             0 hits
audio_pdev               0 hits
SND_SOC_HDMI_CODEC       0 hits
AUDIO_FIFO               0 hits
snd_soc                  0 hits
```

Zero. `v7.1.7` has **no HDMI-RX audio support of any kind** — no codec
registration, no ACR handling, not even the register `#define`s. Nothing is
already applied, from either implementation. (Contrast T10, where the candidate
turned out to be a no-op.)

### Step 1 — the three-check dry run, bare `v7.1.7`

| Patch | `git apply --check` | `git apply --check -R` |
|---|---|---|
| v4 1/4 dt-bindings | **0** (applies) | 1 (not present) |
| v4 2/4 driver | **0** (applies) | 1 (not present) |
| v4 3/4 SoC dtsi | **0** (applies) | 1 (not present) |
| v4 4/4 board dts | **0** (applies) | 1 (not present) |

Forward-clean and confirmed-absent on all four. `--3way` was not needed: it is the
no-op proof, and nothing here is a no-op.

### Step 2 — the real adoption scenario

Upstream v4 in place of `0005`+`0006`, layered on the video half of our series:

```
$ git am --keep-non-patch patches/0001-*.patch patches/0002-*.patch patches/0003-*.patch
  base video patches applied OK
$ for p in v4-{0001..0004}; do git apply --check -p1 $p.mbox; done
  v4-0001-dt-bindings      forward-check: OK
  v4-0002-driver           forward-check: OK
  v4-0003-dtsi             forward-check: OK
  v4-0004-opi5plus         forward-check: OK
$ git am --keep-non-patch v4-0001 v4-0002 v4-0003 v4-0004
  Applying: dt-bindings: media: snps,dw-hdmi-rx: add #sound-dai-cells
  Applying: media: synopsys: hdmirx: add HDMI audio capture support
  Applying: arm64: dts: rockchip: add HDMI RX audio on RK3588
  Applying: arm64: dts: rockchip: enable HDMI RX audio capture on Orange Pi 5 Plus
  ALL FOUR APPLIED
```

No conflict with `0001` (encoder), `0002` (EDID) or `0003` (plugout) — v4 2/4
touches `hdmirx_suspend`/`hdmirx_resume` and `hdmirx_probe`, which none of those
three rewrite.

**Prerequisite commits: none.** The series stands alone on `v7.1.7`. The two
kernel facilities it needs are already present: `no_i2s_playback` /
`no_spdif_playback` exist in `include/sound/hdmi-codec.h` (lines 125–129), and
`/schemas/sound/dai-common.yaml#` exists for the binding.

So the answer to "would it apply?" is an unqualified yes. It is declined on
merit and on criterion 6, not on mechanics.

---

## Criterion 4 — behaviour on both shipped boards' DT

**This is where adoption breaks, and it breaks hard.** `kernel-pin.env` pins
`ARMBIAN_BOARDS="rock-5b-plus orangepi5-plus"` — two boards, both shipped.

State of the base, before anything is applied:

| Board at `v7.1.7` | `&hdmi_receiver` | `&i2s7_8ch` | sound card |
|---|---|---|---|
| `rk3588-rock-5b.dtsi` | enabled | **not referenced** | none |
| `rk3588-orangepi-5-plus.dts` | enabled | **not referenced** | none |

That is the KEY FACT state: receiver on, no card. Now compare the two candidates
after applying, measured on the actual trees:

| | `0005` + `0006` (today) | upstream v4 |
|---|---|---|
| SoC card node | `hdmirx_sound` in `rk3588-extra.dtsi`, `status = "disabled"` | `hdmi_receiver_sound` in `rk3588-extra.dtsi`, `status = "disabled"` |
| `#sound-dai-cells` on `hdmi_receiver` | `<0>` | `<1>` |
| Codec reference | `sound-dai = <&hdmi_receiver>` | `sound-dai = <&hdmi_receiver 0>` |
| `simple-audio-card,mclk-fs` | `<128>` | **absent** |
| Card name | `"hdmirx"` | `"RK3588 HDMI-IN"` |
| **Orange Pi 5 Plus** | card + `i2s7_8ch` enabled | card + `i2s7_8ch` enabled |
| **Rock 5B+** | card + `i2s7_8ch` enabled | **NEITHER** |

Measured on the adopted tree:

```
rk3588-rock-5b.dtsi              hdmi_receiver_sound:0  i2s7_8ch:0
rk3588-orangepi-5-plus.dts       hdmi_receiver_sound:1  i2s7_8ch:1
```

Upstream 4/4 is titled *"enable HDMI RX audio capture on Orange Pi 5 Plus"* and
does exactly and only that. **Adopting the series as posted silently removes
HDMI-RX audio from Rock 5B+** — one of the two boards CeraLive ships — and
reinstates precisely the failure mode `image-building-pipeline/AGENTS.md` records:

> **HDMI-RX audio needs BOTH patch `0005` and patch `0006` — `0005` alone gives a
> bound codec and NO ALSA card.**

The failure is invisible without hardware: the codec device binds, `dmesg` is
clean, nothing reports an error, and `/proc/asound/cards` simply lacks the fifth
card. This is the exact shape of bug that cost a full diagnosis cycle already.

The repository gate catches it, which is the one piece of good news. Running
`apply.sh`'s post-apply assertions against the adopted tree:

```
  ok      hdmirx registers an ASoC codec device
  MISSING dts node hdmirx_sound in rk3588-extra.dtsi
  MISSING dts node hdmirx_codec_dai in rk3588-extra.dtsi
  MISSING #sound-dai-cells = <0> on hdmi_receiver
  MISSING &hdmirx_sound in rk3588-rock-5b.dtsi
  MISSING &i2s7_8ch in rk3588-rock-5b.dtsi
  MISSING &hdmirx_sound in rk3588-orangepi-5-plus.dts
  ok      rk3588-orangepi-5-plus.dts enables &i2s7_8ch
```

Six of eight audio assertions fail. Note the shape of that output: three failures
are cosmetic (the gate greps for our label `hdmirx_sound`, upstream's is
`hdmi_receiver_sound`), but **`MISSING &i2s7_8ch in rk3588-rock-5b.dtsi` is not
cosmetic** — no relabelling makes it pass, because the enablement genuinely is not
there.

> **NOT tested on hardware.** No RK3588 board is reachable from this repository.
> Nothing above was observed on a Rock 5B+ or an Orange Pi 5 Plus with a real HDMI
> source and `arecord`. Every claim is read out of the `v7.1.7` source tree, the
> published series, and the post-apply state of a scratch worktree. The one
> hardware datapoint in evidence is the field report behind the standing
> instruction, and it is about the in-house pairing, not the candidate.

The `mclk-fs` row is flagged and deliberately **not** adjudicated: `0006` sets
`simple-audio-card,mclk-fs = <128>` and upstream's card does not. Whether that
matters when the receiver is bitclock/frame master is a hardware question, and
this document does not guess at it.

---

## Criterion 5 — known-defect fixes included

Neither implementation carries a `Fixes:` tag; neither is a defect fix. The
honest accounting is of defects each one *has*, and which the other repairs.

**Defects in `0005` that upstream v4 would fix:**

| Defect | Severity here | Why it has not bitten us |
|---|---|---|
| Audio worker not cancelled across system suspend — register access on gated clocks | Real, latent | CeraLive devices are always-on streaming appliances; suspend is not in the product's lifecycle. `hdmirx_suspend()` is `__maybe_unused` and only reached via `SET_SYSTEM_SLEEP_PM_OPS` |
| Playback DAIs registered on a capture-only device | Cosmetic | An operator sees a playback stream that does nothing. No functional impact on capture |
| `hdmirx_audio_hw_params()` accepts S/PDIF and returns 0 | Unreachable | `#sound-dai-cells = <0>` makes DAI 1 unaddressable from our DT |
| `hdmirx_audio_startup()` is dead code (`if (…) return 0; return 0;`) | Cosmetic | No behaviour |

**Defects in upstream v4 that `0005` does not have** — items 1–4 of criterion 1's
second table, plus the author's own open bug: *a second suspend/resume cycle in
the same boot can leave the audio datapath silent until reboot*.

**Neighbourhood sweep.** `v7.1.7`'s `synopsys/hdmirx` contains no audio code at
all, so there is no third-party fix in the neighbourhood to weigh — unlike `0002`,
where a stable backport was already sitting in the base. The Collabora capture
lists exactly one HDMI-RX audio row and this series is it. No other posting was
found touching `snps_hdmirx` audio.

---

## Criterion 6 — the `0006` interplay (the extra criterion)

> **`0006` is NOT superseded, and it CANNOT be carried alongside the upstream
> series. Under adoption it would have to be rewritten from scratch, and the
> rewrite would be strictly larger than what it replaces.**

This is the criterion that decides the task, so it is answered mechanically.

### The two DT halves are competitors, not complements

`0006` and upstream 3/4 edit **the same two regions of the same file**:

| Hunk | `0006` | upstream 3/4 |
|---|---|---|
| Card node insertion | `rk3588-extra.dtsi @@ -23,6 +23,30 @@` | `rk3588-extra.dtsi @@ -23,6 +23,23 @@` |
| `hdmi_receiver` property | `@@ -338,6 +362,7 @@` → `#sound-dai-cells = <0>` | `@@ -338,6 +355,7 @@` → `#sound-dai-cells = <1>` |

Proven, not inferred — `0006` against a tree with upstream v4 applied:

```
$ git apply --check -p1 patches/0006-rk3588-hdmirx-audio-sound-card.patch
error: patch failed: arch/arm64/boot/dts/rockchip/rk3588-extra.dtsi:338
error: arch/arm64/boot/dts/rockchip/rk3588-extra.dtsi: patch does not apply
exit=1
```

And the conflict is semantic as well as textual: `#sound-dai-cells` cannot be
both `<0>` and `<1>` on one node, so `sound-dai = <&hdmi_receiver>` and
`sound-dai = <&hdmi_receiver 0>` are mutually exclusive spellings of the same
link. Carrying both halves is not merely awkward, it is ill-formed.

### The three possible answers, and which one is true

| Answer | True? | Why |
|---|---|---|
| `0006` **stays required as-is** | ✅ **under the KEEP verdict** | Nothing changes. `0005`+`0006` remain the pairing, unmodified |
| `0006` **needs adaptation** | ⚠️ *only if v4 is adopted* | It would have to be replaced by a new first-party patch enabling `&hdmi_receiver_sound` + `&i2s7_8ch` on `rk3588-rock-5b.dtsi` — upstream covers Orange Pi 5 Plus only |
| `0006` **is superseded** | ❌ **false** | Upstream 3/4 supersedes the *SoC-level* half of `0006`. It does **not** supersede the board-level half for Rock 5B+, which upstream never touches |

The seductive reading — *"upstream brings its own DT bindings, so our first-party
DT patch goes away"* — is wrong. Adoption does not retire `0006`; it retires two
of `0006`'s three jobs and leaves the third orphaned, on the board that would
silently lose audio.

### What adoption would actually cost

Not "swap two patches". Concretely:

1. Retire `0005` through the `retired/REGISTRY.md` state machine (move, register, drop from `SERIES`).
2. Retire `0006` the same way, or rewrite it.
3. Import four unmerged patches into `backports/` with **no upstream SHA to record** — the lane's provenance contract (`commit <sha> upstream.`) cannot be satisfied by a series that is not merged.
4. Author a **new** first-party patch re-adding Rock 5B+ enablement against upstream's `hdmi_receiver_sound` label.
5. Rewrite `apply.sh`'s post-apply assertions for the new node names and the new cell arity.
6. Re-verify a config path we currently guarantee via `select SND_SOC_HDMI_CODEC`.
7. Accept a known-silent-audio suspend bug and lose multichannel, jack reporting and cable-pull teardown.

Seven steps, on a working, field-proven pairing, to track a series that no
maintainer has yet applied.

---

## Verdict

> **KEEP `0005` and `0006` as they stand. The upstream PATCHv4 series is
> adoptable but not adopted: it is not strictly better, and its device-tree half
> would silently remove HDMI-RX audio from Rock 5B+.**

Against the bar the user set:

1. **Strictly better?** **No.** Four genuine improvements (suspend, capture-only
   flags, S/PDIF refusal, upstream shape) against six genuine regressions
   (multichannel, jack reporting, plugout teardown, pre-capture clock lock,
   self-contained Kconfig, rate-validity gate). A trade, not an upgrade.
2. **Cleanly applicable?** **Yes** — and it is recorded as a yes precisely so
   nobody re-runs this test. All four apply forward with no fuzz to `v7.1.7`, and
   on top of `0001`–`0003`. This is not why it is declined.
3. **`0006` interplay resolved cleanly?** **No.** `0006` is neither superseded nor
   compatible; adoption requires deleting it and writing a replacement to
   re-cover Rock 5B+. The `0005`+`0006` pairing is load-bearing and would be
   broken, not migrated.
4. **The standing instruction** — *"in-house is already working very well"* —
   applies with full force. The in-house pairing is the only implementation of
   this feature that has been observed working on both shipped boards.

**Series impact: none.** No file moves to `retired/`, nothing is added to
`backports/`, `patches/` regenerates byte-identically, `retired/REGISTRY.md`
stays empty. The gate was re-run afterwards to prove exactly that.

### What a future adoption would need

This verdict is explicitly re-openable. Re-evaluate when **all** of the following
hold — the first two are non-negotiable, the third is what makes it safe:

1. **The series is merged.** A real mainline SHA exists, so `backports/` can carry
   honest `commit <sha> upstream.` provenance and the retire trigger on the
   `0005` row can key off a version instead of a hope.
2. **Rock 5B+ is covered** — either by a follow-up upstream patch enabling
   `&hdmi_receiver_sound` + `&i2s7_8ch` on `rk3588-rock-5b.dtsi`, or by an
   explicit decision to author that as a first-party patch and say so.
3. **The functional regressions are closed or accepted on the record:**
   multichannel/speaker-allocation, jack reporting via `hook_plugged_cb` (Dmitry
   named this himself as future work), and audio teardown in `hdmirx_plugout()`.
   Also confirm the author's known "silent after a second suspend/resume cycle"
   bug is fixed, since suspend support is the main thing being bought.

A cheaper intermediate exists and is worth naming: **backport only the suspend
handling into `0005`** as a small first-party change (cancel the worker in
`hdmirx_suspend()`, re-arm in `hdmirx_resume()`). That captures the single
defect fix worth having without touching the DT, without breaking the `0006`
pairing, and without importing an unmerged series. It is not proposed here —
this task's charter is adopt-or-keep — but it is the obvious next move if suspend
ever becomes part of the product's lifecycle.

### What stays open

- **Hardware-gated, unchanged:** none of this is board-verified. The multichannel,
  jack and plugout advantages claimed for `0005` are read from source; they have
  not been demonstrated against a 5.1 source or a mid-stream cable pull.
- **`dtbs_check`:** `0006` adds `#sound-dai-cells` to a node whose binding does not
  yet allow it. Upstream 1/4 is the fix for that, and it is `Reviewed-by`
  Krzysztof Kozlowski. If we ever run `dtbs_check` in CI, that binding patch alone
  becomes worth importing — independently of the rest of the series.
</content>
