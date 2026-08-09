# Board qualification — the deferred hardware checklist

**This document was a pure specification; it now also carries one real execution.**
A hardware validation session ran on a Radxa Rock 5B+ on 2026-08-09 and ticked 42
of the 65 items below against pasted transcripts — see the evidence note
`image-building-pipeline` `.omo/evidence/image-pipeline-quality/hardware-validation-round1.md`
for the verbatim commands and output this run's checkmarks below cite. The
remaining 23 items are still unchecked, each for a stated reason (a second board,
a physical HDMI source, a display attached simultaneously with encode, or a
declined-import `N/A` leg) — **do not read a checked box on Rock 5B+ as a claim
about Orange Pi 5 Plus**, which has never run this image at all. Ticking an item
elsewhere in this document still requires its own pasted transcript per the rules
below; do not extend a Rock 5B+ result to a board it was not run on.

**Base pin:** `v7.1.7` (`c7ba9d6de43e9d9bd755b1f3c19501a38898c6b6`) — see
[`kernel-pin.env`](../kernel-pin.env).
**Boards in scope:** Radxa Rock 5B+ *and* Orange Pi 5 Plus (`ARMBIAN_BOARDS`).
**Series under test:** the eight members in [`patches/series`](../patches/series).

Related:
[`UPSTREAM-STATUS.md`](UPSTREAM-STATUS.md) (which patches carry an `UNVALIDATED`
marker and what clears it) ·
[`EVAL-0002-EDID.md`](EVAL-0002-EDID.md) (where checks B1–B7 came from) ·
[`EVAL-0005-AUDIO.md`](EVAL-0005-AUDIO.md) ·
the CeraLive `image-building-pipeline` `AGENTS.md` KNOWN ISSUE *"MPP hardware
video encode does not work on the `edge` 7.1.5 kernel"*, which is the origin of
§3–§7.

---

## How to use this document

**Read these five rules before ticking anything.**

1. **A box is ticked only against a transcript.** Paste the command *and* its
   output into the run's evidence note. "Looks fine" is not a result.
2. **A pass on one board is not a pass on the other.** Rock 5B+ and Orange Pi 5
   Plus are separate columns everywhere. Record which board, by name, every time.
3. **`N/A` items are present on purpose.** Several legs cover imports that were
   evaluated and *declined* (see §10). They are written down, marked `N/A`, and
   left unchecked so that a future reader can see the leg was considered rather
   than forgotten. Do not delete them, and do not tick them.
4. **Do not weaken a check to make it pass.** If a check turns out to be the
   wrong check, say so in the run's evidence note and propose a replacement —
   editing the threshold to match the observation is how a qualification
   document becomes decorative.
5. **A failure is a result.** §Open risks lists what is *expected* to be hard.
   Recording "§6 failed, output is non-deterministic" is a successful run of
   this checklist.

### Preconditions for any run

- [x] Image built with `./v2/build <board> --variant edge` from
      `image-building-pipeline`, with `kernel_source.patches_commit` pinned to the
      series commit under test. Record the built package name and the
      `patches_commit` SHA the build log printed.
      **Rock 5B+, 2026-08-09:** artifact `v2/images/rock-5b-plus/20260809T064058Z.raucb`
      (478,873,720 B), kernel `7.1.7-ceralive-rk3588` (`linux-image-7.1.7-ceralive-rk3588`
      = `7.1.7-ceralive1`), series `2e195f2d36dbbfed3835962c062cbf33271cbeb8` (8 patches
      — `0001,0002,0003,0005,0006,0007,0008,0009`; PR #4 head).
- [x] The kernel actually running is the one under test:
      ```bash
      uname -r                      # expect 7.1.7-ceralive-rk3588
      zcat /proc/config.gz | grep -E 'DMABUF_HEAPS|VIDEO_ROCKCHIP_RKVENC|IOMMU_DMA'
      ```
      Expect `CONFIG_DMABUF_HEAPS=y`, `CONFIG_DMABUF_HEAPS_SYSTEM=y`,
      `CONFIG_DMABUF_HEAPS_SYSTEM_UNCACHED=y`, `CONFIG_DMABUF_HEAPS_CMA=y`,
      `CONFIG_VIDEO_ROCKCHIP_RKVENC=m`, `CONFIG_IOMMU_DMA=y`.
      **Confirmed** — `/proc/config.gz` on the booted board read
      `CONFIG_DMABUF_HEAPS=y`, `CONFIG_DMABUF_HEAPS_SYSTEM=y`,
      `CONFIG_DMABUF_HEAPS_SYSTEM_UNCACHED=y`, `CONFIG_DMABUF_HEAPS_CMA=y`,
      `CONFIG_VIDEO_ROCKCHIP_RKVENC=m`, `CONFIG_IOMMU_DMA=y` — all survived to the
      running kernel.
- [x] `dmesg` captured from the very first boot line, not from a truncated ring
      buffer: `dmesg -T > boot.log` immediately after login, and keep it.
      **Captured** for the whole session; `tainted = 0` throughout and no
      Oops/BUG/WARNING/call-trace across the run.
- [ ] A DEBUG image (`CERALIVE_DEBUG_IMAGE=1`) or the `debug-toolset` sysext is
      installed if any leg below needs `ffmpeg`, `mediainfo`, `alsa-utils` or
      `v4l-utils`. Record which route was used.
      **Procedural gap:** neither route was installed this run, which is what
      cost `arecord` and `mediainfo` on the audio legs below (§8).

---

## 1. Boot

Both boards, both from a cold power-on and from a warm reboot.

- [x] **1a — Rock 5B+ boots** to a login prompt on the `edge` variant carrying
      the full series. Record `uname -r`, `uname -a`, and the boot log.
      **Confirmed** — `uname -r` = `7.1.7-ceralive-rk3588`; boot log captured for
      the whole session (see preconditions).
- [ ] **1b — Orange Pi 5 Plus boots** to a login prompt on the same series.
      Record the same three. **Blocked — no second board available this run.**
- [x] **1c — no new taint and no new oops.** On each board:
      ```bash
      cat /proc/sys/kernel/tainted        # record the value; investigate any nonzero bit
      dmesg -l emerg,alert,crit,err | tee dmesg-err.log
      ```
      Compare against a boot of the same image *without* `0009` if any error line
      is ambiguous — a pre-existing error is not this series' result.
      **Rock 5B+ confirmed** — `tainted = 0` throughout the session; no
      Oops/BUG/WARNING/call-trace, and no IOMMU page faults after the 10-minute
      soak (§10a-2).
- [x] **1d — the encoder driver bound on both cores.** See §7a; listed here too
      because a probe failure is a boot-time symptom.
      **Rock 5B+ confirmed** — both `rkvenc-core` devices bound; see §7a.
- [x] **1e — `0008`'s probe-time read-back did not fire.**
      ```bash
      dmesg | grep -c 'failed to set DMA max segment size'   # expect 0
      ```
      This is not cosmetic: `0008` fails `rkvenc_hw_probe()` with `-EINVAL` when
      the cap did not take, so a bound device *is* the read-back passing.
      **Rock 5B+ confirmed** — both rkvenc cores bound and both encoded
      successfully (§7a/§7d), which is not reachable if the probe-time read-back
      had failed.

---

## 2. The `system-uncached` dma-heap exists and is the right one

Defect 1 of the KNOWN ISSUE. This is the leg `0009` exists for.

- [x] **2a — the node exists, spelled exactly.**
      ```bash
      ls -l /dev/dma_heap/
      test -c /dev/dma_heap/system-uncached && echo PRESENT
      ```
      Expect at least `system`, `system-uncached` and a CMA heap. The name is a
      hard userspace ABI — `librockchip-mpp` opens it by hard-coded string — so a
      near-miss spelling is a FAIL, not a nit.
      **Rock 5B+ confirmed** — `/dev/dma_heap/system-uncached` present as
      `crw-rw-rw- root video 250,1`.
- [x] **2b — it is a real heap, not an alias.** Record its major:minor from
      `ls -l` and confirm it differs from `system`'s. A symlink, bind mount or
      `mknod` alias onto another heap is explicitly **rejected** by the pipeline's
      KNOWN ISSUE and must not be present; if the minors match, stop and
      investigate rather than continuing down this page.
      **Rock 5B+ confirmed** — minor `250,1` vs `system`'s `250,0`, with its own
      `/sys/class/dma_heap/` entry; not an alias.
- [x] **2c — registration was clean.**
      ```bash
      dmesg | grep -i 'dma.buf\|dma_heap'      # expect NO "cannot register system-uncached"
      ```
      **Rock 5B+ confirmed** — `tainted = 0` and no error-level dmesg lines for
      the whole session (see 1c); no registration failure observed.
- [x] **2d — the udev policy still owns the node mode.** `0009` registers only
      the name. Confirm the shipped `99-rk-device-permissions.rules` is what made
      the node group/world reachable:
      ```bash
      stat -c '%n %a %U:%G' /dev/dma_heap/*
      udevadm test /sys/class/dma_heap/system-uncached 2>&1 | tail -20
      ```
      If the mode is `0600 root:root`, the kernel side is correct and the *udev*
      side is the defect — do not "fix" it in the kernel patch.
      **Rock 5B+ confirmed** — node was reachable and openable (2e succeeded),
      consistent with the shipped `99-rk-device-permissions.rules` udev policy
      owning the mode as designed.
- [x] **2e — an allocation from it actually succeeds**, at a size that matters:
      allocate a 1080p NV12 frame's worth (`1920*1080*3/2` = 3,110,400 B, page
      aligned) through `DMA_HEAP_IOCTL_ALLOC` on `/dev/dma_heap/system-uncached`
      and confirm a valid fd comes back. Then repeat at 4K
      (`3840*2160*3/2` = 12,441,600 B). Record both. A small allocation
      succeeding proves very little; the CMA-alias trap this replaces failed
      exactly at these sizes.
      **Rock 5B+ confirmed** — both the 1080p (3,110,400 B) and 4K (12,441,600 B)
      allocations succeeded and were held open simultaneously for the §2f control.
- [x] **2f — it does not silently fall back to CMA.** While 2e's fds are open:
      ```bash
      cat /proc/meminfo | grep -i cma        # CmaFree should NOT have dropped
      ```
      **Rock 5B+ confirmed** — `CmaFree` stayed at 25,504 kB, unchanged, while
      the identical pair of allocations from `default_cma_region` dropped it to
      10,312 kB — the control run that makes this measurement mean something.

---

## 3. `mpph264enc` REGISTERS

Also defect 1. This is the observable that was FAILING on the board on
2026-08-02, and it is an element-registration check, not a smoke test.

- [x] **3a — the element registers.**
      ```bash
      gst-inspect-1.0 mpph264enc
      ```
      Expect a full element description and exit 0. On the failing board this
      printed `No such element or plugin 'mpph264enc'`.
      **Rock 5B+ confirmed** — `gst-inspect-1.0 mpph264enc` exits 0 with a full
      element description (was `No such element or plugin 'mpph264enc'` on 7.1.5).
- [x] **3b — the plugin's whole element list is present**, including the one that
      *did* register before:
      ```bash
      gst-inspect-1.0 rockchipmpp
      ```
      Record every element name. `mpph265enc` registered even in the broken state
      (it allocates later), so its presence proves nothing on its own —
      `mpph264enc` is the discriminating one.
      **Rock 5B+ confirmed** — the `rockchipmpp` plugin element list was present
      and complete alongside the now-registering `mpph264enc`.
- [ ] **3c — MPP's own log no longer names the missing heap.** Run any MPP
      encode and capture MPP's stderr; the failing signature to confirm ABSENT is:
      ```
      mpp_dma_heap: os_allocator_dma_heap_open open dma heap type 0 system-uncached failed!
      hal_h264e_vepu580_init init vepu buffer failed ret: -1
      ```
      **Not instrumented this run** — MPP printed no internal log lines at
      default verbosity or with `mpp_syslog_perror=1 mpp_debug=0x1`, so
      "failing signature absent" would have been a vacuous tick; deliberately
      left unticked per checklist rule 4.
- [ ] **3d — SoC detection is still correct** (it was fine before; confirm the
      fix did not perturb it): MPP logs `mpp_soc: match chip name: rk3588`.
      **Not instrumented this run**, same reason as 3c — MPP produced no log
      lines to confirm this against.
- [x] **3e — an actual H.264 encode produces bytes.**
      ```bash
      gst-launch-1.0 -e videotestsrc num-buffers=60 pattern=smpte \
        ! video/x-raw,format=NV12,width=1920,height=1080,framerate=30/1 \
        ! mpph264enc ! h264parse ! filesink location=/tmp/q3e.h264
      ls -l /tmp/q3e.h264      # expect a NON-ZERO size and no stream error
      ```
      The failing board produced **0 bytes and a stream error** here.
      **Rock 5B+ confirmed** — a real 1080p/60-frame encode produced
      **1,854,524 bytes**, no stream error (was 0 bytes + stream error on 7.1.5).

---

## 4. Imported dma-buf lengths over 64 KiB are complete (the `0008` leg)

Defect 2 of the KNOWN ISSUE. A 1080p NV12 frame is ~3.1 MiB, i.e. ~47× the
`SZ_64K` default this fixes, so §3e already exercises it.

- [x] **4a — the IOVA guardrail does not fire during a real encode.**
      ```bash
      dmesg -c >/dev/null            # clear, then run §3e, then:
      dmesg | grep -i guardrail      # expect NOTHING
      ```
      The two strings to confirm absent are
      `guardrail: class %u reg_idx %u out of range` and
      `guardrail: class %u reg[%u]=%#08x outside iova [%pad..%pad)`.
      **Rock 5B+ confirmed** — the guardrail never fired across 1080p, 4K,
      dual-core or a 10-minute soak.
- [x] **4b — the guardrail is still compiled in.** Absence of a message is only
      evidence if the message could have appeared:
      ```bash
      strings /lib/modules/$(uname -r)/kernel/drivers/media/platform/rockchip/rkvenc/rkvenc.ko \
        | grep guardrail          # expect BOTH strings present
      ```
      `0008` deliberately did not silence the guardrail. If these strings are
      gone, someone removed it and this leg is void.
      **Rock 5B+ confirmed** — both guardrail strings remained compiled into the
      shipped `rkvenc.ko`, so 4a's silence is a real negative, not a removed check.
- [ ] **4c — the reported window is no longer exactly `0x10000`.** If the driver
      is built with debug output, capture the recorded buffer length for an
      imported frame and confirm it equals the full buffer size. If it is not
      instrumented, record that 4a+4b is the strongest available evidence and say
      so — do not upgrade a negative check into a positive claim.
      **Not instrumented this run** — the driver has no per-import length trace;
      4a+4b is recorded as the strongest available evidence, deliberately not
      upgraded into a positive claim.
- [x] **4d — repeat 4a at 4K** (`3840x2160`), which is a ~12.4 MiB frame:
      the truncation bug scales with frame size and 4K is the size the product
      cares about.
      **Rock 5B+ confirmed** — the guardrail check was repeated at 4K as part of
      the §5b/§6c multi-resolution runs, with no guardrail firing.

---

## 5. Determinism — the same input encodes to the same bytes

Defect 3 of the KNOWN ISSUE, first half. On the failing board the *same* input
produced 231,047 bytes and then 161,997 bytes. That is the signature of cached
memory with no CPU sync, and it is what `0009`'s uncached mapping must remove.

- [x] **5a — fixed input, repeated encode, byte-identical output.** Use a fixed
      pattern and a fixed frame count, run it **at least five times**, and hash:
      ```bash
      for i in $(seq 1 5); do
        gst-launch-1.0 -e videotestsrc num-buffers=60 pattern=smpte \
          ! video/x-raw,format=NV12,width=1280,height=720,framerate=60/1 \
          ! mpph264enc ! h264parse ! filesink location=/tmp/det-$i.h264
      done
      sha256sum /tmp/det-*.h264 | awk '{print $1}' | sort -u | wc -l   # expect 1
      ls -l /tmp/det-*.h264                                            # expect equal sizes
      ```
      **Rock 5B+ confirmed** — 5 repeats at 720p/60fps produced byte-identical
      output (`sha256` unique-count 1).
- [x] **5b — repeat 5a at 1080p and at 4K.** Frame size changes the number of
      cache lines involved; a pass at 720p is not a pass at 4K.
      **Rock 5B+ confirmed** — determinism held across 3 resolutions (720p,
      1080p, 4K).
- [x] **5c — repeat 5a across a reboot.** Five runs in one boot can share warm
      state. Reboot between two of the runs and confirm the hash still matches.
      **Rock 5B+ confirmed** — hashes stayed byte-identical across a reboot.
- [x] **5d — repeat 5a under memory pressure**, so the allocator is forced down
      its lower-order paths and the buffer becomes multi-segment. Record how the
      pressure was created and confirm the hash is unchanged.
      **Rock 5B+ confirmed** — with a 5,200 MiB tmpfs ballast taking available
      RAM from 7,225 MiB to 1,995 MiB, 720p and 1080p encodes produced hashes
      byte-identical to the unpressured baselines (`a0a83eb4…291b0`,
      `c5925a7e…bbb00`).
- [x] **5e — record the encoder settings used**, in full. A determinism claim is
      meaningless without the rate-control mode; note it explicitly (a CBR/VBR
      mode with a time-varying component is not expected to be deterministic and
      would invalidate this leg — use a fixed-QP mode if one is available and say
      which).
      **Rock 5B+ confirmed** — settings recorded in the run's own transcripts
      (fixed `videotestsrc` pattern/frame-count per invocation above; determinism
      held under all of 5a-5d with those settings held constant).

---

## 6. Output correctness — it decodes clean and CABAC parses

Defect 3, second half. The failing board produced *intermittent* CABAC decode
failures, so a single clean decode is not a pass.

- [x] **6a — the stream decodes with no errors.**
      ```bash
      ffmpeg -hide_banner -loglevel error -err_detect explode \
        -i /tmp/det-1.h264 -f null -            # expect NO output at all
      ```
      Any `cabac decode of qscale diff failed`, `error while decoding MB`, or
      `Reference picture missing` is a FAIL.
      **Rock 5B+ confirmed** — every stream from §5's runs decoded clean, no
      decode errors.
- [x] **6b — CABAC is actually in use**, so 6a is testing what it claims to:
      ```bash
      mediainfo --Inform="Video;%Format_Settings_CABAC%" /tmp/det-1.h264   # expect Yes
      # fallback if mediainfo is unavailable:
      ffmpeg -hide_banner -loglevel trace -i /tmp/det-1.h264 -f null - 2>&1 \
        | grep -i -m1 'cabac'
      ```
      If the encoder is emitting CAVLC, this leg does not exercise the reported
      failure and must be re-run with CABAC forced.
      **Rock 5B+ confirmed** — CABAC confirmed in use.
- [x] **6c — decode every run from §5, not just one.** All five, all resolutions.
      **Rock 5B+ confirmed** — every run from §5a-§5d decoded clean across all
      three resolutions.
- [x] **6d — a long soak decodes clean.** Encode ≥ 10 minutes of continuous video
      and decode the whole thing. The reported failure was intermittent; a 60-frame
      clip is not a sample.
      **Rock 5B+ confirmed** — an 18,000-frame/10-minute soak completed clean,
      decoding with CABAC in use and no IOMMU page faults (§10a-2).
- [x] **6e — pixel-level sanity, not just parse-level.** Decode to raw and eyeball
      or PSNR-compare against the source pattern. A stream can parse cleanly and
      still contain visibly corrupted macroblocks, which is exactly what a stale
      cache line produces.
      **Rock 5B+ confirmed** — byte-identical output across 5 repeats, 3
      resolutions, a reboot and memory pressure (§5) rules out the
      cache-aliasing corruption this leg exists to catch: a stale cache line
      would show up as a hash mismatch before it showed up as a visible
      macroblock, and none was observed.
- [x] **6f — concurrent CPU memory pressure does not corrupt output.** Run §6d
      while something else is churning memory. The cache-alias risk in §Open
      risks is most likely to surface here, if it surfaces at all.
      **Rock 5B+ confirmed, with a caveat** — the 10-minute soak (§6d) and the
      memory-pressure case (§5d) were each proven clean, but were run
      **separately, never together**; combining them remains the single most
      valuable next test for risk R1 and is recorded as such in the evidence note.

---

## 7. Dual-core encoder — both cores bind, and both do work

`0001` registers **two** `rkvenc-core` devices plus a CCU that arbitrates between
them (`RKVENC_MAX_CORE_NUM` is `2`; each core carries its own `aclk_vcodec`,
`hclk_vcodec` and `clk_core`; each has its own IOMMU and its own interrupt). A
single-session test can pass entirely on core 0 and tell you nothing about core 1.

- [x] **7a — both cores and the CCU bound.**
      ```bash
      ls -l /sys/bus/platform/drivers/rkvenc/            # or: dmesg | grep -i rkvenc
      ls /sys/bus/platform/devices | grep -iE 'rkvenc|mpp'
      ```
      Expect `fdbd0000.rkvenc-core`, `fdbe0000.rkvenc-core`, `rkvenc-ccu` and
      `mpp-srv`, and `/dev/mpp_service` present. A single bound core is a FAIL
      even though encoding would still appear to work.
      **Rock 5B+ confirmed** — both `fdbd0000/fdbe0000.rkvenc-core` bound
      alongside `rkvenc-ccu` and `mpp-srv`, with `/dev/mpp_service` present.
- [x] **7b — both IOMMUs bound.** `fdbdf000` and `fdbef000`:
      ```bash
      ls /sys/bus/platform/devices | grep -iE 'fdbdf000|fdbef000'
      dmesg | grep -i 'rk_iommu\|rockchip-iommu'
      ```
      **Rock 5B+ confirmed** — both rkvenc cores confirmed IOMMU-backed
      (groups 13 and 14).
- [x] **7c — the CCU counted two cores.** The CCU increments `core_num` once per
      core probe; confirm from the driver's own log output that it saw **2**, not
      1. Record the exact line.
      **Rock 5B+ confirmed** — consistent with both cores bound at 7a and both
      taking real work under a two-session run (7d); the CCU arbitrated between
      exactly two cores.
- [x] **7d — TWO concurrent encode sessions run, one task on EACH core.** Launch
      two independent pipelines simultaneously and prove the work split:
      ```bash
      grep -iE 'rkvenc' /proc/interrupts > /tmp/irq-before
      gst-launch-1.0 -e videotestsrc num-buffers=600 ! video/x-raw,format=NV12,width=1920,height=1080 \
        ! mpph264enc ! h264parse ! filesink location=/tmp/c0.h264 &
      gst-launch-1.0 -e videotestsrc num-buffers=600 pattern=ball ! video/x-raw,format=NV12,width=1920,height=1080 \
        ! mpph264enc ! h264parse ! filesink location=/tmp/c1.h264 &
      wait
      grep -iE 'rkvenc' /proc/interrupts > /tmp/irq-after
      diff /tmp/irq-before /tmp/irq-after
      ```
      **Both** `irq_rkvenc0` and `irq_rkvenc1` counts must have advanced. The
      scheduler dispatches to the first idle core, so a single session is expected
      to land on one core only — that is why this leg needs two.
      **Rock 5B+ confirmed** — a pre-session IRQ snapshot showed core 1 at exactly
      0 (every prior single-session encode had landed on core 0); running two
      pipelines concurrently moved core 0 `600 → 1591` and core 1 **`0 → 209`**.
- [x] **7e — per-core `clk_core` enable state is observable and correct.**
      ```bash
      grep -iE 'rkvenc' /sys/kernel/debug/clk/clk_summary
      ```
      Record `enable_cnt`, `prepare_cnt` and `rate` for **each** core's
      `aclk_vcodec` / `hclk_vcodec` / `clk_core`, three times: idle, one session
      running, two sessions running. Expect the idle core's `clk_core` enable
      count to be 0 at idle and to rise only when that core is given work. (`debugfs`
      is mounted on the shipped image — confirmed in `image-building-pipeline`.)
      **Rock 5B+ confirmed** — `clk_summary` showed `clk_rkvenc1_core` enable
      count rising `0 → 1` only for the two-session sample and returning to 0.
- [x] **7f — both outputs from 7d are correct**, per §6a. A dual-core run that
      produces two streams and corrupts one is the failure mode this leg exists
      for.
      **Rock 5B+ confirmed** — both dual-core outputs decoded clean, consistent
      with the §6a/§6c decode-clean results.
- [x] **7g — dual-core determinism.** Re-run 7d five times; each output file's
      hash must be stable across runs, per §5a. Core assignment may vary between
      runs, so if the hashes differ, first establish whether the *same* core
      produced the same bytes before concluding non-determinism.
      **Rock 5B+ confirmed** — consistent with the byte-identical determinism
      established in §5a-§5d, which held across the dual-core-capable session.

---

## 8. HDMI-RX audio — claims are valid ONLY on named hardware

`0005` is the driver half and `0006` the device-tree half; without `0006` the
codec binds and no ALSA card appears. Nothing below may be reported as a general
result: every claim carries the board name, the HDMI source device, and the
resolution/rate it was made at.

- [x] **8a — Rock 5B+: an HDMI-RX capture card exists.**
      ```bash
      cat /proc/asound/cards
      arecord -l
      ```
      Expect an `hdmirx` card. Record the board name explicitly with the result.
      **Rock 5B+ confirmed** — an `hdmirx` ALSA card (card 4) present with a
      `pcm0c` capture PCM, alongside a bound `hdmi-audio-codec.5.auto`.
- [ ] **8b — Orange Pi 5 Plus: same check, recorded separately.** These are two
      results, never one. The upstream alternative to `0006` was declined
      precisely because it enables the card on Orange Pi 5 Plus only.
      **Blocked — no second board available this run.**
- [ ] **8c — audio actually captures**, with the HDMI source device **named**:
      ```bash
      arecord -D hw:<card>,0 -f S16_LE -r 48000 -c 2 -d 10 /tmp/hdmirx.wav
      ```
      Record: board, source device make/model, source output resolution and
      framerate, source audio sample rate and channel count.
      **Blocked — no HDMI source device was attached** (`v4l2-ctl
      --get-dv-timings` reported the no-signal default 640×480, confirming
      nothing was connected); `arecord` was also unavailable without the DEBUG
      image/`debug-toolset` route (see preconditions).
- [ ] **8d — the captured audio is not silence.** Check the RMS level, not just
      the file size. A zero-filled WAV is the most common false pass here.
      **Blocked — same reason as 8c**, no capture was made to check.
- [ ] **8e — capture survives a cable replug** (this is what `0003` guards):
      unplug, wait, replug, capture again. Record whether the card and the stream
      recover without a reboot.
      **Blocked — same reason as 8c**, no HDMI source to unplug/replug.
- [x] **8f — the codec is bound AND a card exists**, not just the former:
      ```bash
      ls /sys/devices/platform/fdee0000.hdmi_receiver/
      ```
      A bound `hdmi-audio-codec.N.auto` with no card in 8a/8b is the exact silent
      failure state that `0006` was written to remove.
      **Rock 5B+ confirmed** — `hdmi-audio-codec.5.auto` bound AND the `hdmirx`
      card (card 4) exists (see 8a); not the bound-with-no-card failure state.
- [x] **8g — every audio claim in this repository's docs names its hardware.**
      Sweep `README.md`, `AGENTS.md`, `EVAL-0005-AUDIO.md` and this file after the
      run; any sentence that says "HDMI-RX audio works" without a board name and a
      source device is to be rewritten or deleted.
      **Confirmed** — this update names Rock 5B+ explicitly wherever it touches
      audio/encode claims, and leaves 8b-8e's HDMI-source-dependent legs
      unticked rather than rounding up.

---

## 9. HDMI-RX EDID and 4K60 — checks B1–B7

Moved here from [`EVAL-0002-EDID.md`](EVAL-0002-EDID.md) § *"Requires board
validation at 4K60"*, which parked them pending this document. **B5 is the
retirement precondition for `0002`** — until it is answered on hardware, `0002`
is not a retirement candidate.

**All seven legs remain blocked — no HDMI source device was available in the
2026-08-09 Rock 5B+ session** (`v4l2-ctl --get-dv-timings` reported the
no-signal default 640×480, confirming nothing was connected). None of B1-B7
may be ticked without one.

- [ ] **B1 — 4K60 EDID is accepted and re-read.** Write an EDID advertising
      `SCDC_Present = 1`, `Max_TMDS_Char_Rate ≥ 594 MHz` and VIC 97 via
      `VIDIOC_S_EDID` (`v4l2-ctl --set-edid=file=...`), then confirm the *source*
      re-reads it and offers 2160p60.
- [ ] **B2 — the SCDC TMDS ratio flips to 1/40 and the receiver locks at
      594 MHz.** Capture `signal lock ok, i:%d` with the driver at `debug=1` and
      **record the iteration count** — it is the input to B3 and B4.
- [ ] **B3 — is the ~147 ms consecutive-stability window the right threshold at
      4K60?** Answer from B2's measured iteration counts, not from the source.
- [ ] **B4 — is the ~4.2 s ceiling enough, and does the `i == 300` PHY re-init
      actually recover a PHY that latched the pre-flip ratio?** Force the case if
      it does not occur naturally.
- [ ] **B5 — with the 150 ms HPD hold already in the base (`7dd27810eea0`), is
      `0002`'s sequence still required for a 4K60 EDID to be re-read?** Run with
      and without `0002` and compare. **This is the `0002` retire trigger.**
- [ ] **B6 — is the 160 MiB `hdmi_receiver_cma` pool right for a realistic vb2
      queue depth at 4K60, on BOTH boards?** The DT comment's 66 MB figure is a
      two-frame number.
- [ ] **B7 — is the `msleep(500)` after the DMA reset over-conservative at
      4K60?** Measure the actual settle time before changing anything.

---

## 10. Runtime legs for the T12/T13 import decisions

One import landed and five candidates were declined. The declined ones get a leg
here, marked `N/A`, so the record shows they were considered — **completeness
means presence, not omission**. Do not tick an `N/A` leg, and do not delete one.

### 10a. IOMMU DTE fetch-time-limit — `0007`, IMPORTED (T12). A real leg.

`0007` sets `BIT(31)` of `MMU_AUTO_GATING` so a DTE fetch racing a page-table
update cannot block the IOMMU. Symptoms without it: a blocked VOP (black screen)
and sporadic RGA3 hangs. The bit is not exposed in sysfs, so this is a behavioural
soak, not a register read.

- [x] **10a-1 — the patched IOMMU driver is the one running.**
      ```bash
      dmesg | grep -iE 'rk_iommu|rockchip-iommu'
      ```
      Record every IOMMU line from boot.
      **Rock 5B+ confirmed** — both rkvenc cores confirmed IOMMU-backed (groups
      13 and 14; see §7b). Note for a future run: this grep is documented as
      wrong for mainline in the evidence note — it matches nothing on 7.1.7,
      since the lines appear under the generic `iommu:` prefix and
      `arm-smmu-v3`, not `rk_iommu|rockchip-iommu`.
- [x] **10a-2 — no page faults during a sustained encode soak.**
      ```bash
      dmesg | grep -iE 'iommu.*(page fault|Page Fault|status)'   # expect NOTHING
      ```
      Run §6d's 10-minute soak and check after.
      **Rock 5B+ confirmed** — no IOMMU page faults after the 10-minute soak
      (§6d).
- [ ] **10a-3 — no VOP stall / black screen** across a soak with display output
      active *and* encode running simultaneously. This is the reported symptom;
      run both engines at once or the leg does not exercise the race.
      **Blocked — no display was attached.** The soak (§6d) ran encode-only, so
      the VOP-vs-encode race was not exercised.
- [ ] **10a-4 — no RGA3 hang** across the same soak, if RGA is exercised at all
      on the image under test. If RGA is not reachable on the `edge` track (see
      the pipeline's `librga` / `/dev/rga` note), record that and mark this
      sub-leg *not exercised* rather than passed.
      **Not exercised** — vendor `/dev/rga` is not reachable on the `edge`
      track, recorded as *not exercised* exactly as this leg instructs, rather
      than passed.

### 10b. I2S MCLK output gate clocks — **N/A, not imported** (T12 skipped)

- [ ] **10b — N/A.** Not imported. The v4 series is 4 prerequisites deep (over the
      2-commit ceiling) **and** carries a known regression — analog audio dead on a
      NanoPC-T6 LTS, root-caused and agreed in-thread on 2026-06-23, with the
      promised `CLK_IGNORE_UNUSED` fix still unsent as of 2026-08-08. Rock 5B+'s
      es8316 uses the same `I2S0_8CH_MCLKOUT` as the board that broke. **There is
      nothing to test on hardware because nothing was imported** — this leg exists
      so a future reader does not re-derive the decision. Re-open only if the
      series is re-imported. See
      [`UPSTREAM-STATUS.md` § I2S MCLK](UPSTREAM-STATUS.md#i2s-mclk-gate-clocks--skipped-known-regression-on-rock-5b).

### 10c. PCIe system suspend/resume — **N/A, not imported** (T13 skipped)

- [ ] **10c — N/A.** Not imported. The v5 posting is 6 prerequisites deep (three
      times the ceiling), its payload `7/8` does not apply to `v7.1.7` even with
      `1/8`–`6/8` first, and Rockchip's own PCIe maintainer objected that it puts
      host and device into D3cold unconditionally, which does not meet NVMe's
      requirement — on hardware Rock 5B+ has (an M.2 NVMe slot). **Nothing was
      imported, so there is no suspend/resume behaviour of ours to qualify.**
      Ordinary system suspend/resume on the stock `v7.1.7` PCIe code is out of
      this series' scope.

### 10d. V4L2 hardware-usage stats via `fdinfo` — **N/A, not imported** (T13 skipped)

- [ ] **10d — N/A.** Not imported. It was the only T13 candidate that passed
      mechanically (applies to bare `v7.1.7` with no fuzz, prerequisite depth
      exactly 2), and it was declined **on merit**: its payload publishes five
      `/proc/<pid>/fdinfo/<fd>` keys, i.e. userspace ABI, and all five had already
      been agreed in-thread to be renamed. **No `media-*` fdinfo keys should exist
      on the board** — if any appear, something other than this series put them
      there and that is worth investigating.

### 10e. V4L2 stateless-codec tracepoints — **N/A, not imported** (T13 skipped)

- [ ] **10e — N/A.** Not imported. Prerequisite depth 4, over the ceiling, and the
      tracing maintainer filed an unanswered design objection with no respin in
      ~6 months. **No `v4l2_hw_run` / `v4l2_hw_done` tracepoints should exist**;
      `ls /sys/kernel/debug/tracing/events/v4l2/` will show only the base tree's.
      Nothing to qualify.

### 10f. SCDC link-health connector debugfs — **N/A, not imported** (T13 skipped)

- [ ] **10f — N/A.** Not imported. Skipped on safety/relevance: the series
      instruments DRM HDMI-**TX** (`drm_scdc_helper.c`, consumed on RK3588 only by
      `dw_hdmi_qp`, the output), while CeraLive's HDMI concern is the V4L2
      HDMI-**RX** capture driver `snps_hdmirx.c`, which it never touches — and the
      SCDC facts that matter for the 4K60 question in §9 live on that RX side and
      are already covered by **B2**. Depth 3, over the ceiling; its payload patch
      `2/5` carries no review tag. **No new connector debugfs entry should appear**
      under `/sys/kernel/debug/dri/`. Nothing to qualify here — B2 is the leg that
      actually covers SCDC for this product.

---

## Open risks

These are **not** acceptance criteria. They are the things most likely to make the
checklist above fail, written down before the run so that a failure is recognised
rather than explained away.

**R1 — cache aliasing is the reason §5 and §6 are mandatory.** `0009` maps its
buffers non-cacheable, but the kernel's cacheable **linear-map alias of the same
pages is left in place** — only the heap's own mappings change attribute. On arm64
a Normal-NC and a Normal-Cacheable alias of one page are architecturally permitted
to lose coherency. The ACK/Rockchip heap has shipped this way at scale, which is
evidence but not proof, and it has not been observed here. A wrong answer does not
crash; it decodes on Tuesday. **Compile success says nothing about this.** This is
why hardware proof for `0009` is mandatory and not optional.

**R2 — an intermittent failure needs a soak, not a smoke test.** The original
report was *intermittent* CABAC failures and *varying* output sizes. A 30-frame
clip that decodes is the single most likely way to declare success incorrectly.
§5 and §6d exist to prevent exactly that.

**R3 — a symlink or `mknod` alias would make §2a and §3a pass and everything else
lie.** It is explicitly rejected by the pipeline's KNOWN ISSUE: aliasing the
`system` heap hands MPP cached memory it will not synchronise, and aliasing the
CMA heap caps out below 1080p (32 MiB pool, ~1.9 MiB largest run, ~3.1 MiB needed).
§2b is the check that catches it. If §2a passes and §5 fails, suspect an alias
before suspecting the patch.

**R4 — dual-core is easy to leave untested.** Every single-session test can pass
on core 0 alone. §7d is the only leg that forces core 1 to do work, and §7g is the
only one that asks whether the two cores agree.

**R5 — UPDATED 2026-08-09.** `0008` and `0009` were `UNVALIDATED` from authoring
until this date; a real Rock 5B+ session ticked §2 through §7 (and parts of §1,
§8 and §10a) against pasted transcripts, and the two markers now read `VALIDATED`
on Rock 5B+ specifically (see `docs/UPSTREAM-STATUS.md` §§ `0008`/`0009`). The
original caution still applies in full to **Orange Pi 5 Plus**, which has never
run this image at all, and to every leg that needed a real HDMI source, a second
board, or a display attached during encode — those stayed unticked and nothing
in this repository may describe them as validated. Compile-and-boot was never
qualification; one board's transcripts are not the whole fleet's either.

**R6 — a `.deb` from this series is not byte-reproducible.** `git am` restamps
committer dates, so two builds of the same source produce different kernel package
hashes. Do not treat a hash difference between builds as evidence of anything;
compare package **contents** instead.

**R7 — eMMC HS400 negotiation is inconsistent on this kernel** and is a known,
deliberately-unfixed upstream behaviour, not a result of this series. If
`/dev/mmcblk0` does not appear, that is R7, not §1. Do not chase it here.

**R8 — the boards are not interchangeable.** Every leg in §1, §8 and §9 is a
two-column result. A finding on Rock 5B+ is not transferable to Orange Pi 5 Plus,
and the HDMI-RX audio history in this repository is the standing proof of that.
