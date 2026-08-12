# Board qualification — the deferred hardware checklist

**RUN 1 executed 2026-08-09 on a Radxa Rock 5B+.** This document was written as a
pure *specification* of what a real board must demonstrate before anything in this
series may be described as working, and for its first revision nothing in it had
been run. That is no longer true: §2–§7 and §10a-1/§10a-2 are now ticked against
transcripts from real hardware, and the boxes that remain unticked are unticked
because they were **not reachable in that session**, not because they were skipped.
Every tick below carries the command and the observed output inline. **Orange Pi 5
Plus has now run §2–§7** (Run 3, 2026-08-12) — see R8; a Rock 5B+ result was never
transferable, and this is why. Outside that scope, Orange Pi 5 Plus remains entirely unrun on §1b, §8b–§8e, §9 and §10a-3/§10a-4: Run 3 covered only §2–§7,
with no HDMI source, no second board and no display attached, same constraints
as Run 1 on Rock 5B+.

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

## Run log

| Run | Date | Board | Kernel | Series commit | Evidence |
|-----|------|-------|--------|---------------|----------|
| 1 | 2026-08-09 | Radxa Rock 5B+ | `7.1.7-ceralive-rk3588` (`7.1.7-ceralive1`) | `2e195f2d36dbbfed3835962c062cbf33271cbeb8` | `image-building-pipeline` `.omo/evidence/image-pipeline-quality/hardware-validation-round1.md` |
| 2 | 2026-08-10 → 2026-08-12 | Radxa Rock 5B+ **and** Orange Pi 5 Plus | `7.1.7-ceralive-rk3588` (production) and `7.1.7-ceralive-rk3588-test` (KASAN + `PROVE_LOCKING` + `DEBUG_ATOMIC_SLEEP`) | `eb0f338edd6b203387ea22b4aceb6eb57136c68c` | `image-building-pipeline` `test-results/pipeline-restructure-kernel-backports/wave8/` — signed receipts 33/34/35/36/37/45 (Rock, debug), 46 (Rock, production), 47 (Orange Pi, production) |
| 3 | 2026-08-12 | Orange Pi 5 Plus | `7.1.7-ceralive-rk3588` | `eb0f338edd6b203387ea22b4aceb6eb57136c68c` | `.omo/evidence/orange-pi-run3/RAW-EVIDENCE.md` (this repo) |

**Run 1 headline.** All three stacked defects of the pipeline's *"MPP hardware
video encode does not work on the `edge` 7.1.5 kernel"* KNOWN ISSUE are **resolved
on this board**: `/dev/dma_heap/system-uncached` exists as a real, distinct heap
(§2), `mpph264enc` registers (§3a) and encodes (§3e), the IOVA guardrail never
fires (§4a) while remaining compiled in (§4b), output is byte-identical across
repeats, resolutions, a reboot and memory pressure (§5), decodes clean with CABAC
in use including a 10-minute soak (§6), and **both** encoder cores take real work
(§7d, core 1 IRQ `0 → 209`).

**Run 1 scope limits, stated up front.** The board had **no HDMI source attached**
and **no second board**, so §1b, §8b–§8e, all of §9, and §10a-3 could not be run.
The image under test was a **PRODUCTION** image (no `CERALIVE_DEBUG_IMAGE`, no
`debug-toolset` sysext), which ships `ffmpeg`/`ffprobe`/`v4l2-ctl` but **not**
`alsa-utils`, `mediainfo` or `python3`; that cost `arecord -l` in §8a and
`mediainfo` in §6b, both of which were substituted and the substitution recorded.

**Run 2 headline.** Run 1 asked whether the series works. Run 2 asked what *breaks* it,
on both boards, with fault injection against a debug kernel — and got answers.
**Eight real defects were found and fixed**, none of which compile-and-boot could have
surfaced, and every one of them found by forcing a negative path rather than by
observing a failure in the wild:

- **B — release imbalance.** `rkvenc_task_finish()` unconditionally handed back a
  reset-group `rw_sem`, two runtime-PM references, a wakeup source and three clocks
  that `rkvenc_hw_run()` holds across a return **only on success**, so every failed
  dispatch produced a `bad unlock balance` next to a `Runtime PM usage count
  underflow!`. One `TASK_STATE_HW_HELD` bit consumed with `test_and_clear_bit()`
  covers all five and makes the teardown single-shot.
- **C — missing ioctl/UAPI bounds.** The register-write check demanded exact byte
  coverage, and **no two of the nine register classes abut**, so any request running
  off a class edge landed in a hole and was refused — MPP's own 96-byte `BASE` write
  (4 bytes short of the class end) was merely the shape that reached it first.
  Replaced by a contiguity test derived from the declared table, with zero constants.
  **Its first form carried its own regression**, which the next board run caught and
  which was amended in place before the series moved on.
- **F — worker use-after-free.** `rkvenc_task_worker_default()` read `mpp_task->state`
  after `rkvenc_task_finish()` had woken a waiter that could already have dropped the
  last reference and freed the task. Pre-existing in `0001`; not introduced by B's fix.
- **G — core 1 loses its IOMMU domain on unbind.** A secondary core that unbound and
  re-bound came back with a NULL domain and `rkvenc_iommu_attach()` dereferenced it.
  The pre-existing `domain == iommu_get_domain_for_dev()` guard could not catch it,
  because the default domain that call returns is never NULL.
- **D — service-node teardown lifetime**, in three parts. The unbind returned into a
  `remove()` that freed a `devm`-allocated `srv` which a still-open descriptor then
  took a mutex on (`BUG: KASAN: slab-use-after-free in __mutex_lock`, at close time,
  10 s after an unbind that had already "completed"); the quiesce logged *"refusing to
  release service state"* and released it anyway; and a **third sub-defect**, reachable
  only by the negative fixture — `rkvenc_service_sessions_gone()` took `session_lock`
  from inside a `wait_event*()` **condition**, which `___wait_event()` evaluates after
  `prepare_to_wait_event()` has set the task state (`WARNING … __might_sleep`). It had
  never fired anywhere because `wait_event_timeout()` short-circuits when zero sessions
  are open, so only a drain with a descriptor still open ever reaches the second
  evaluation. `srv` is now reference-counted rather than `devm`-allocated, and the
  condition is a lockless `READ_ONCE()`.
- **Finding J — HDMI-RX CEC hardirq lockdep violation**, in the **upstream**
  `synopsys_hdmirx` driver rather than in anything this series wrote. `rst_lock` is
  declared `spinlock_t` (`LD_WAIT_CONFIG`) and taken from hardirq (`LD_WAIT_SPIN`) —
  exactly the reported `{3:3}` inside `context-{2:2}`, and not a false positive. CEC
  only won the race to report it first: with a 4K30 source attached `/proc/interrupts`
  showed `rk_hdmirx_cec` at **1** interrupt against `rk_hdmirx-hdmi` at **37**, and
  `debug_locks_off()` hid the other 37. Fixing only the CEC read would have relocated
  the report and looked like a fix on any board with no source attached.

**Run 2 — how the fixes were confirmed.** Every one of the above was re-verified on
real hardware at the final series commit, not cross-referenced from the run that found
it. The debug board ran the **full 12-command fault-injection block** — every `rkvenc`
bind-time knob, the clock-enable fault, the delayed teardown, all four
`rkvenc-unbind.sh` states plus the supplementary `timeout-negative` fixture, the
HDMI-RX audio worker and clock faults, and a whole-boot kernel-log screen either side —
**with lockdep genuinely armed for the entire run**, which is a first for this campaign
and is the single most load-bearing fact in this entry. `/proc/lockdep_stats` read
`debug_locks: 1` on the first command of a fresh cold boot *and* still `1` after the
whole workload; the earlier runs' identical all-zero sweeps were **vacuous**, because
finding J had already tripped `debug_locks_off()` before a shell existed. Both
production candidates additionally ran the 11-command hardware drill clean. Encode
figures were byte-for-byte reproducible across every build and both boards: 1080p
**1,854,524 B**, 4K **7,390,209 B**, dual concurrent **19,206,933 B** each and
bit-identical, 20/20 SIGTERM cycles with the element still registered. The four
`rkvenc-unbind.sh` states passed with `all devices rebound consumer-after-supplier` in
every one, over 20 cycles, with 1,854,524 B after each. **Eight hardware evidence
receipts** were signed and independently verified (`exit 0`, against a pre-bound run
key, with `patches_commit`, `tested_a_commit`, the A-tree hash, `patches_applied=22`
and the bundle SHA-256 all asserted on the command line): 33/34/35/36/37/45 on the Rock
5B+ debug kernel, 46 on the Rock 5B+ production candidate, 47 on the Orange Pi 5 Plus.
The late patch consolidation was proven **content-neutral** before those receipts were
re-signed against it — identical git tree object over the applied series, and a
byte-identical extracted kernel `.config` on both boards.

**Run 2 — two findings resolved as non-blockers, deliberately and with reasons.**
**Defect H** is §11: a *kernel-side task failure does not reach the application*
because `librockchip-mpp` races the driver's `-ENODEV`. It is real and measured, it is
**not a kernel defect**, and nothing in this repository can fix it — so it is
documented rather than chased, and run 2 replaced the QA assertion that was measuring
it (see the end of §11). **Defect A** is a `possible recursive locking` report on the
reset-group `rw_sem`: core 1 is only ever selected while core 0 has a task in flight,
so every core-1 dispatch nests `down_read()` on the one shared rwsem in the one worker
thread. lockdep is right, but the nesting **cannot deadlock today** — `grep` finds no
`down_write` on that rwsem anywhere in the driver. Its real harm was that
`debug_locks_off_graph_unlock()` blinded lockdep for the rest of the boot, which is
precisely why "lockdep armed the whole run" is called out above. It did not fire at all
in the final runs, with lockdep armed to have caught it.

**Run 2 scope, corrections and limits, stated up front.** Two inherited board facts
were **wrong and were corrected against the boards themselves** rather than carried
forward: the Rock 5B+ **does** have a real 58.3 GB eMMC (`mmcblk0`, type `MMC`, name
`HCG8e`, plus `mmcblk0boot0`/`boot1`; it boots from SD, which is why the eMMC set sits
idle), so its eMMC leg is a genuine bounded `O_DIRECT` read and not an `N/A`
substitution; the Orange Pi 5 Plus genuinely does **not** — its `mmc0`
(`fe2e0000.mmc`) enumerates zero cards and only `mmcblk1` exists, so `emmc=none-fitted`
there is a real board fact. The same re-derivation applied to the radios: Wi-Fi and
Bluetooth are real on the Rock and absent on the Orange Pi, while USB3 is the reverse.
Copying one board's `N/A` markers onto the other would have fabricated results on a
unit that can satisfy them, which is R8 in practice rather than in principle. Still
open, and unticked: §8b–§8e and §9 on the Orange Pi 5 Plus remain blocked upstream of
this series by the `snps_hdmirx` TF-A/BL31 probe failure (unrelated to finding J, which
is a later code path in a driver that on that board never probes at all); the
`UNVALIDATED` markers in [`UPSTREAM-STATUS.md`](UPSTREAM-STATUS.md) were again **not**
cleared, for the same reason run 1 did not clear them; and two harness defects proven
this run are recorded rather than fixed — the `valid-after-failures` fixture off-by-one
and the HDMI-RX clock case's unbounded single-sample read, which cost up to 12 retries
of unmodified frozen command text against a servo whose inter-arrival time is measured
at 1.4 s to >30 s. Both are **test** defects that read as driver results, which is the
same class of mistake §11 exists to prevent.

**Run 3 headline.** Run 3 answered the question Run 1/Run 2 left open on the second
board: does §2–§7 hold on Orange Pi 5 Plus, not just Rock 5B+? It does. Every leg in
§2–§7 that has a Rock 5B+ Run-1 annotation now has a matching Orange Pi 5 Plus
result, and of the legs with a directly comparable Rock byte count or hash, eight
matched Rock **byte-for-byte**: §3e (1,854,524 B), §4d (3,742,992 B), §5a's hash,
§5b's 4K hash, §5e's fixqp hash, §6d's soak (583,117,763 B), and both §7d/§7g file
sizes and hashes. **One did not**: §5b's 1080p determinism hash differs from Rock's
recorded 1080p hash, even though Orange Pi's own three repeats at that resolution
were internally consistent (unique = 1). This is reported honestly below rather than
smoothed over — see §5b — and it does not weaken the determinism finding, because
determinism as this document defines it is a per-board, same-input-same-output
claim, not a cross-board byte-identity requirement; the byte-identity on the other
eight legs is bonus corroborating evidence, not the pass criterion itself. Run 3 was
scoped to §2–§7 only: no HDMI source, no second board and no display were involved,
so §1b, §8b–§8e, §9 and §10a-3/§10a-4 on Orange Pi 5 Plus remain exactly as open as
they were after Run 2.

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
      **RUN-1 (Rock 5B+): PASS.** Build log printed
      `patches https://github.com/CERALIVE/rk3588-kernel-patches.git commit=2e195f2d36dbbfed3835962c062cbf33271cbeb8 series=patches/series`
      and `patches repo: 2e195f2… verified in /src/patches (attempt 1/3)`; 8 patches applied.
      Built package: `linux-image-7.1.7-ceralive-rk3588=7.1.7-ceralive1/arm64`;
      board DTB `/usr/lib/linux-image-7.1.7-ceralive-rk3588/rockchip/rk3588-rock-5b-plus.dtb`.
      Artifact `20260809T064058Z.raucb` (`sha256 f55ae8cf…30472`), pipeline commit `d685010`.
      *Note:* the build used the documented BENCH local-clone escape hatch
      (`BENCH: patch series fetched from local clone … commit … is still asserted
      after checkout`), so the SHA assertion held but this is not a release-path build.
- [x] The kernel actually running is the one under test:
      ```bash
      uname -r                      # expect 7.1.7-ceralive-rk3588
      zcat /proc/config.gz | grep -E 'DMABUF_HEAPS|VIDEO_ROCKCHIP_RKVENC|IOMMU_DMA'
      ```
      Expect `CONFIG_DMABUF_HEAPS=y`, `CONFIG_DMABUF_HEAPS_SYSTEM=y`,
      `CONFIG_DMABUF_HEAPS_SYSTEM_UNCACHED=y`, `CONFIG_DMABUF_HEAPS_CMA=y`,
      `CONFIG_VIDEO_ROCKCHIP_RKVENC=m`, `CONFIG_IOMMU_DMA=y`.
      **RUN-1 (Rock 5B+): PASS.** `uname -r` → `7.1.7-ceralive-rk3588`;
      `uname -a` → `Linux ceralive 7.1.7-ceralive-rk3588 #ceralive1 SMP PREEMPT @1786241725 aarch64`;
      `dpkg -l` → `hi  linux-image-7.1.7-ceralive-rk3588  7.1.7-ceralive1  arm64`.
      All six expected symbols read back from the **running** kernel's `/proc/config.gz`
      exactly as specified, plus `CONFIG_RTW89=m`, `CONFIG_RTW89_8852BE=m`,
      `CONFIG_NF_TABLES=y`, `CONFIG_NF_TABLES_INET=y`, `CONFIG_TYPEC_FUSB302=m`.
      The negative sweep for `# CONFIG_(DMABUF_HEAPS_SYSTEM_UNCACHED|RTW89|NF_TABLES|TYPEC_FUSB302) is not set`
      returned nothing.
- [x] `dmesg` captured from the very first boot line, not from a truncated ring
      buffer: `dmesg -T > boot.log` immediately after login, and keep it.
      **RUN-1 (Rock 5B+): PASS.** `boot.log`, 790 lines, captured immediately after
      the second boot of the slot, first line present. Kept with the evidence note.
      *Caveat, recorded rather than hidden:* an earlier batch ran `dmesg -c`, which
      cleared the ring buffer of the FIRST boot; the reboot required by §5c was used
      to retake a complete, uncleared log, and §2c/§10a-1 were read from that one.
- [ ] A DEBUG image (`CERALIVE_DEBUG_IMAGE=1`) or the `debug-toolset` sysext is
      installed if any leg below needs `ffmpeg`, `mediainfo`, `alsa-utils` or
      `v4l-utils`. Record which route was used.
      **RUN-1 (Rock 5B+): NEITHER ROUTE USED — left unticked deliberately.** The image
      under test was PRODUCTION (`/etc/ceralive/debug-image` absent). It happens to ship
      `ffmpeg`, `ffprobe` and `v4l2-ctl`, which covered §6 and the §8/§9 V4L2 probes,
      but it ships **no `alsa-utils`, no `mediainfo`, no `python3`**. Consequences,
      each recorded at its own leg: §8a used `/proc/asound/cards` + `/proc/asound/hdmirx/`
      instead of `arecord -l`; §6b used `ffmpeg -bsf:v trace_headers` instead of
      `mediainfo`; §2e used a purpose-built statically-linked aarch64 `DMA_HEAP_IOCTL_ALLOC`
      probe instead of a Python one. A future run that needs §8c–§8e **must** install one
      of the two routes — `arecord` is not substitutable.

---

## 1. Boot

Both boards, both from a cold power-on and from a warm reboot.

- [x] **1a — Rock 5B+ boots** to a login prompt on the `edge` variant carrying
      the full series. Record `uname -r`, `uname -a`, and the boot log.
      **RUN-1: PASS (warm reboot × 2).** Booted from the microSD's slot B —
      `/proc/cmdline` = `root=PARTLABEL=xrootfs_b rootwait rw console=ttyS2,1500000 earlycon cera_slot=B rauc.slot=B`.
      `uname -r` / `uname -a` / `boot.log` recorded under Preconditions above.
      SSH reachable both times. **Limit:** the session was remote with no power
      control, so **cold power-on was NOT exercised** — only two warm reboots.
- [ ] **1b — Orange Pi 5 Plus boots** to a login prompt on the same series.
      Record the same three.
      **RUN-1: NOT RUN — no Orange Pi 5 Plus available this session.** Per R8 the
      Rock 5B+ result above is explicitly NOT transferable to this row.
- [x] **1c — no new taint and no new oops.** On each board:
      ```bash
      cat /proc/sys/kernel/tainted        # record the value; investigate any nonzero bit
      dmesg -l emerg,alert,crit,err | tee dmesg-err.log
      ```
      Compare against a boot of the same image *without* `0009` if any error line
      is ambiguous — a pre-existing error is not this series' result.
      **RUN-1 (Rock 5B+): PASS.** `/proc/sys/kernel/tainted` → `0`, re-checked after
      every encode batch and after the 10-minute soak — still `0`.
      `dmesg | grep -iE 'Oops|BUG:|WARNING:|call trace'` → **no matches**.
      26 error-level lines, none of them attributable to this series:
      `rockchip-pm-domain … Failed to create device link (0x180) with supplier 1-0042` ×2
      and `… with supplier spi2.0` ×1 (PMIC/SPI supplier ordering);
      `sdhci-dwcmshc fe2e0000.mmc: Can't reduce the clock below 52MHz in HS200/HS400 mode` ×4
      (this is **R7**, not §1 — and note the eMMC still enumerated fine: `mmcblk0` p1–p4 present);
      `hid-generic … device has no listeners, quitting` ×2;
      `dwhdmiqp-rockchip fde80000.hdmi: i2c read error` ×16 (HDMI **TX**, no monitor attached);
      `debugfs: 'Capture' already exists in 'dapm'` ×1.
      No no-`0009` comparison boot was needed — none of the above touches
      dma-buf, rkvenc or the IOMMU.
- [x] **1d — the encoder driver bound on both cores.** See §7a; listed here too
      because a probe failure is a boot-time symptom.
      **RUN-1 (Rock 5B+): PASS.** See §7a/§7c for the transcript; both
      `fdbd0000.rkvenc-core` and `fdbe0000.rkvenc-core` report `probe success`.
- [x] **1e — `0008`'s probe-time read-back did not fire.**
      ```bash
      dmesg | grep -c 'failed to set DMA max segment size'   # expect 0
      ```
      This is not cosmetic: `0008` fails `rkvenc_hw_probe()` with `-EINVAL` when
      the cap did not take, so a bound device *is* the read-back passing.
      **RUN-1 (Rock 5B+): PASS.** Count = `0`, on both boots. Corroborated by §7a:
      both cores are bound, which per this leg's own reasoning *is* the read-back
      passing. The format string `failed to set DMA max segment size to %u` is
      present in the shipped `rkvenc.ko` (see §4b method), so the zero count is a
      real negative and not a missing message.

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
      **RUN-1 (Rock 5B+): PASS.** `test -c` → `PRESENT`. Four heaps, exact spellings:
      ```
      crw------- 1 root root  250, 2 default_cma_region
      crw------- 1 root root  250, 3 reserved
      crw------- 1 root root  250, 0 system
      crw-rw-rw- 1 root video 250, 1 system-uncached
      ```
      `system`, `system-uncached` and a CMA heap all present. Re-verified identically
      after the §5c reboot.
      **RUN-3 (Orange Pi 5 Plus): PASS.** `ls -l /dev/dma_heap/` →
      ```
      crw------- 1 root root  251, 2 default_cma_region
      crw------- 1 root root  251, 3 reserved
      crw------- 1 root root  251, 0 system
      crw-rw-rw- 1 root video 251, 1 system-uncached
      ```
      PRESENT, all four heaps, exact spellings. Minors are `251.x` here vs Rock's
      `250.x` — expected, a different SoC instance's device enumeration order; what
      matters is that the four are distinct from each other, which they are.
- [x] **2b — it is a real heap, not an alias.** Record its major:minor from
      `ls -l` and confirm it differs from `system`'s. A symlink, bind mount or
      `mknod` alias onto another heap is explicitly **rejected** by the pipeline's
      KNOWN ISSUE and must not be present; if the minors match, stop and
      investigate rather than continuing down this page.
      **RUN-1 (Rock 5B+): PASS.** Minors are distinct —
      `system` = `250,0`, `system-uncached` = `250,1`,
      `default_cma_region` = `250,2`, `reserved` = `250,3`
      (`stat -c '%n %t:%T'` → `fa:0` / `fa:1` / `fa:2` / `fa:3`).
      Both are character devices, neither is a symlink, and each has its own
      `/sys/class/dma_heap/` entry (`system`, `system-uncached`,
      `default_cma_region`, `reserved`) — i.e. the kernel registered a second heap
      rather than userspace aliasing the first. §2f independently rules out the
      CMA-alias variant of this trap.
      **RUN-3 (Orange Pi 5 Plus): PASS.** `stat -c '%n %t:%T'` →
      `system=fb:0`, `system-uncached=fb:1`, `default_cma_region=fb:2`,
      `reserved=fb:3` — distinct minors, each with its own `/sys/class/dma_heap/`
      entry.
- [x] **2c — registration was clean.**
      ```bash
      dmesg | grep -i 'dma.buf\|dma_heap'      # expect NO "cannot register system-uncached"
      ```
      **RUN-1 (Rock 5B+): PASS, with the method stated.** `dmesg | grep -i 'cannot register'`
      → no matches, read from the complete uncleared boot log. Note the heaps register
      **silently** on this kernel: `grep -iE 'dma.buf|dma_heap|uncached'` returns no lines
      at all, so "no failure message" is on its own weak evidence. It is corroborated by
      2a (all four nodes exist), 2b (distinct minors, own sysfs class entries) and 2e
      (allocations actually succeed) — a heap that failed to register would have no node.
      **RUN-3 (Orange Pi 5 Plus): PASS.** `dmesg | grep -i 'cannot register'` → no
      matches.
- [x] **2d — the udev policy still owns the node mode.** `0009` registers only
      the name. Confirm the shipped `99-rk-device-permissions.rules` is what made
      the node group/world reachable:
      ```bash
      stat -c '%n %a %U:%G' /dev/dma_heap/*
      udevadm test /sys/class/dma_heap/system-uncached 2>&1 | tail -20
      ```
      If the mode is `0600 root:root`, the kernel side is correct and the *udev*
      side is the defect — do not "fix" it in the kernel patch.
      **RUN-1 (Rock 5B+): PASS, and the contrast is the proof.**
      ```
      /dev/dma_heap/default_cma_region 600 root:root
      /dev/dma_heap/reserved           600 root:root
      /dev/dma_heap/system             600 root:root
      /dev/dma_heap/system-uncached    666 root:video
      ```
      Only `system-uncached` is relaxed, and it is relaxed to exactly what the shipped
      rule asks for — `KERNEL=="system-uncached", MODE="0666", GROUP="video"` in
      `/etc/udev/rules.d/99-rk-device-permissions.rules`. The other three heaps keeping
      the kernel default `0600 root:root` is what demonstrates the mode came from **udev
      policy**, not from the patch. Re-verified after the §5c reboot.
      **RUN-3 (Orange Pi 5 Plus): PASS.** `stat -c '%n %a %U:%G' /dev/dma_heap/*` →
      ```
      /dev/dma_heap/default_cma_region 600 root:root
      /dev/dma_heap/reserved 600 root:root
      /dev/dma_heap/system 600 root:root
      /dev/dma_heap/system-uncached 666 root:video
      ```
      Only `system-uncached` relaxed, matching the shipped udev rule — same contrast
      Rock 5B+ showed.
- [x] **2e — an allocation from it actually succeeds**, at a size that matters:
      allocate a 1080p NV12 frame's worth (`1920*1080*3/2` = 3,110,400 B, page
      aligned) through `DMA_HEAP_IOCTL_ALLOC` on `/dev/dma_heap/system-uncached`
      and confirm a valid fd comes back. Then repeat at 4K
      (`3840*2160*3/2` = 12,441,600 B). Record both. A small allocation
      succeeding proves very little; the CMA-alias trap this replaces failed
      exactly at these sizes.
      **RUN-1 (Rock 5B+): PASS at both sizes, both fds held simultaneously.** The image
      ships no `python3`/`gcc`, so a statically-linked aarch64 `DMA_HEAP_IOCTL_ALLOC`
      probe was cross-compiled on the host and run on the board:
      ```
      heap: /dev/dma_heap/system-uncached
      open ok (heap fd 3)
      ALLOC OK     len=3110400  (2.97 MiB)  -> dmabuf fd 4
      ALLOC OK     len=12441600 (11.87 MiB) -> dmabuf fd 5
      EXIT=0
      ```
      **RUN-3 (Orange Pi 5 Plus): PASS at both sizes.** Same probe, cross-compiled and
      run on-board:
      ```
      heap: /dev/dma_heap/system-uncached
      open ok (heap fd 3)
      ALLOC OK     len=3110400  (2.97 MiB)  -> dmabuf fd 4
      ALLOC OK     len=12441600  (11.87 MiB)  -> dmabuf fd 5
      EXIT=0
      ```
      Both 1080p (3,110,400 B) and 4K (12,441,600 B) NV12-frame-sized allocations
      succeeded.
- [x] **2f — it does not silently fall back to CMA.** While 2e's fds are open:
      ```bash
      cat /proc/meminfo | grep -i cma        # CmaFree should NOT have dropped
      ```
      **RUN-1 (Rock 5B+): PASS, with a control run.** While both 2e fds were held,
      `CmaFree` was **unchanged**:
      ```
      [before]        CmaTotal: 32768 kB   CmaFree: 25504 kB
      [while-held]    CmaTotal: 32768 kB   CmaFree: 25504 kB
      [after-release] CmaTotal: 32768 kB   CmaFree: 25504 kB
      ```
      To prove that measurement is not vacuous, the identical two allocations were
      repeated against `/dev/dma_heap/default_cma_region`, where `CmaFree` **did**
      drop by ~15,192 kB — the size allocated:
      ```
      [before]        CmaFree: 25504 kB
      [while-held]    CmaFree: 10312 kB
      [after-release] CmaFree: 22856 kB
      ```
      So `system-uncached` demonstrably does not draw from CMA. This directly
      refutes the CMA-alias half of **R3**.
      **RUN-3 (Orange Pi 5 Plus): PASS, with the same control-run method.** `CmaFree`
      before/while-held/after §2e's fds:
      ```
      system-uncached:      [before] CmaFree: 27040 kB  [while-held] 27040 kB  [after] 27040 kB  (UNCHANGED)
      default_cma_region:    [before] CmaFree: 27040 kB  [while-held] 11848 kB  [after] 22040 kB  (DROPPED then recovered)
      ```
      `system-uncached` does not draw from CMA; the `default_cma_region` control shows
      a real CMA heap DOES show the drop, confirming the measurement methodology.

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
      **RUN-1 (Rock 5B+): PASS — this is the headline result.** Exit `0`, full
      description printed:
      ```
      Factory Details:
        Rank                     primary + 1 (257)
        Long-name                Rockchip Mpp H264 Encoder
        Klass                    Codec/Encoder/Video
      Plugin Details:
        Name                     rockchipmpp
        Filename                 /lib/aarch64-linux-gnu/gstreamer-1.0/libgstrockchipmpp.so
        Version                  1.14.4
      … GstVideoEncoder -> GstMppEnc -> GstMppH264Enc
      ```
      **RUN-3 (Orange Pi 5 Plus): PASS.** `gst-inspect-1.0 mpph264enc` printed a full
      description — `Rockchip Mpp H264 Encoder`, `Klass: Codec/Encoder/Video` — with
      no error, matching Rock 5B+'s result.
- [x] **3b — the plugin's whole element list is present**, including the one that
      *did* register before:
      ```bash
      gst-inspect-1.0 rockchipmpp
      ```
      Record every element name. `mpph265enc` registered even in the broken state
      (it allocates later), so its presence proves nothing on its own —
      `mpph264enc` is the discriminating one.
      **RUN-1 (Rock 5B+): PASS.** 5 features / 5 elements:
      `mpph264enc`, `mpph265enc`, `mppjpegdec`, `mppvideodec`, `mppvpxalphadecodebin`.
      `mpph264enc` — the discriminating one — is present.
      **RUN-3 (Orange Pi 5 Plus): PASS.** Same 5 elements — `mpph264enc`,
      `mpph265enc`, `mppjpegdec`, `mppvideodec`, `mppvpxalphadecodebin` — matching
      Rock 5B+'s count and names.
- [ ] **3c — MPP's own log no longer names the missing heap.** Run any MPP
      encode and capture MPP's stderr; the failing signature to confirm ABSENT is:
      ```
      mpp_dma_heap: os_allocator_dma_heap_open open dma heap type 0 system-uncached failed!
      hal_h264e_vepu580_init init vepu buffer failed ret: -1
      ```
      **RUN-1 (Rock 5B+): NOT INDEPENDENTLY MEANINGFUL — left unticked deliberately.**
      Both signatures are absent from the captured stdout+stderr of a real 1080p encode.
      But MPP emitted **no internal log lines at all** at default verbosity (see 3d),
      and raising it via `mpp_syslog_perror=1 mpp_debug=0x1` surfaced nothing either —
      so "absent" here is close to vacuous and ticking it would be exactly the
      weakening rule 4 forbids. The discriminating evidence for defect 1 is **3a**
      (the element registers) and **3e** (it produces bytes); neither is possible if
      `os_allocator_dma_heap_open` on `system-uncached` had failed, because that is
      what aborts `mpp_init(MPP_CTX_ENC, AVC)` and skips registration. A future run
      that can raise MPP's log level should tick this properly.
- [ ] **3d — SoC detection is still correct** (it was fine before; confirm the
      fix did not perturb it): MPP logs `mpp_soc: match chip name: rk3588`.
      **RUN-1 (Rock 5B+): NOT OBSERVED.** No `mpp_soc` line appeared at default
      verbosity, nor with `mpp_syslog_perror=1 mpp_debug=0x1`. The correct SoC path is
      indirectly evidenced by VEPU580 hardware encode working at all (§3e, §7d), but
      the specific log line this leg names was never printed, so the box stays empty.
- [x] **3e — an actual H.264 encode produces bytes.**
      ```bash
      gst-launch-1.0 -e videotestsrc num-buffers=60 pattern=smpte \
        ! video/x-raw,format=NV12,width=1920,height=1080,framerate=30/1 \
        ! mpph264enc ! h264parse ! filesink location=/tmp/q3e.h264
      ls -l /tmp/q3e.h264      # expect a NON-ZERO size and no stream error
      ```
      The failing board produced **0 bytes and a stream error** here.
      **RUN-1 (Rock 5B+): PASS.** Exactly this command produced
      `-rw-r--r-- 1 root root 1854524 /tmp/q3e.h264` — **1,854,524 bytes**, clean
      `Got EOS from element "pipeline0"`, no stream error. (Was 0 bytes + stream
      error on 7.1.5.)
      **RUN-3 (Orange Pi 5 Plus): PASS.** Exactly this command produced
      `-rw-r--r-- 1 ceralive ceralive 1854524 /tmp/q3e.h264` — **1,854,524 bytes,
      BYTE-FOR-BYTE IDENTICAL to Rock 5B+ Run-1's §3e result.** Clean EOS, no stream
      error.

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
      **RUN-1 (Rock 5B+): PASS.** Ring buffer cleared, §3e run, `dmesg | grep -i guardrail`
      → **no matches**. Re-checked after every subsequent batch — the 4K encodes, the
      dual-core runs, the memory-pressure runs and the 10-minute soak — and it stayed
      clean throughout. `dmesg | grep -i rkvenc` also produced no error lines during
      encodes.
      **RUN-3 (Orange Pi 5 Plus): PASS.** `dmesg | grep -i guardrail` after §3e's
      encode → no matches.
- [x] **4b — the guardrail is still compiled in.** Absence of a message is only
      evidence if the message could have appeared:
      ```bash
      strings /lib/modules/$(uname -r)/kernel/drivers/media/platform/rockchip/rkvenc/rkvenc.ko \
        | grep guardrail          # expect BOTH strings present
      ```
      `0008` deliberately did not silence the guardrail. If these strings are
      gone, someone removed it and this leg is void.
      **RUN-1 (Rock 5B+): PASS.** The image ships no `strings`, so `grep -a` was used
      against the same path on the running board (and cross-checked with `strings` on
      the identical `rkvenc.ko` extracted from the installed bundle). **Both** strings
      present:
      ```
      guardrail: class %u reg_idx %u out of range (%u dwords) fd %d
      guardrail: class %u reg[%u]=%#08x outside iova [%pad..%pad) fd %d
      ```
      So 4a's silence is a real negative.
      **RUN-3 (Orange Pi 5 Plus): PASS.** `grep -a guardrail` against
      `/lib/modules/$(uname -r)/kernel/drivers/media/platform/rockchip/rkvenc/rkvenc.ko`
      returned **both** strings present, identical to Rock 5B+'s result.
- [ ] **4c — the reported window is no longer exactly `0x10000`.** If the driver
      is built with debug output, capture the recorded buffer length for an
      imported frame and confirm it equals the full buffer size. If it is not
      instrumented, record that 4a+4b is the strongest available evidence and say
      so — do not upgrade a negative check into a positive claim.
      **RUN-1 (Rock 5B+): NOT INSTRUMENTED — recorded as this leg instructs.** The
      shipped `rkvenc.ko` emits no per-import buffer-length trace, so the recorded
      window could not be read directly. **4a + 4b is therefore the strongest available
      evidence** — the guardrail is compiled in and provably able to fire, and it did
      not fire across 1080p, 4K, dual-core and a 10-minute soak. That is a negative
      check and is deliberately **not** being upgraded into a positive claim that the
      recorded length equals the buffer size.
- [x] **4d — repeat 4a at 4K** (`3840x2160`), which is a ~12.4 MiB frame:
      the truncation bug scales with frame size and 4K is the size the product
      cares about.
      **RUN-1 (Rock 5B+): PASS.** Ring buffer cleared, 30 frames at `3840x2160` NV12
      encoded → `-rw-r--r-- 1 root root 3742992 /tmp/q4d.h264` (**3,742,992 bytes**),
      clean EOS; `dmesg | grep -i guardrail` → **no matches**. A 4K NV12 frame is
      12,441,600 B ≈ 190× the `SZ_64K` default.
      **RUN-3 (Orange Pi 5 Plus): PASS.** Repeat at 4K (`3840x2160`, 30 frames) →
      `-rw-r--r-- 1 ceralive ceralive 3742992 /tmp/q4d.h264` — **3,742,992 bytes,
      BYTE-FOR-BYTE IDENTICAL to Rock 5B+ Run-1's §4d result.** `dmesg | grep -i
      guardrail` → no matches.

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
      **RUN-1 (Rock 5B+): PASS.** Unique hashes = **1**; all five files 851,388 bytes.
      `a0a83eb40247d9850f702ae464d90c7758b921d287e0aaa61f66885e187291b0` ×5.
      Repeated with `rc-mode=fixqp qp-init=26` (see 5e): unique hashes = **1**,
      all five 2,024,005 bytes, `c53db7706e9472f091b6159c033fb75c6ce937ed0bef494cdf1f8c87a771b545`.
      **RUN-3 (Orange Pi 5 Plus): PASS.** 720p60, 5 repeats:
      `sha256: a0a83eb40247d9850f702ae464d90c7758b921d287e0aaa61f66885e187291b0` ×5,
      **851,388 bytes** ×5, unique hashes = **1**. **HASH IDENTICAL TO ROCK 5B+
      RUN-1.**
- [x] **5b — repeat 5a at 1080p and at 4K.** Frame size changes the number of
      cache lines involved; a pass at 720p is not a pass at 4K.
      **RUN-1 (Rock 5B+): PASS at both.**
      1080p30 ×3 → unique hashes = 1, all 957,790 B,
      `c5925a7ece33908563801048226573cbfc2dcb6120c1229243ee31ea870bbb00`.
      4K (3840×2160) ×3 → unique hashes = 1, all 3,742,992 B,
      `b9d44cc08bf44f2276278fc99c64001c010a06e5d506ba616a989d4c7b7d543d`.
      1080p `fixqp` ×3 → unique hashes = 1,
      `d320d5762b645b354f9a71d68da8f281e3ee9dab9731495afa762782a1fcb978`.
      **RUN-3 (Orange Pi 5 Plus): PASS at 1080p and at 4K, WITH ONE HONEST
      DISCREPANCY at 1080p.**
      1080p ×3 → unique hashes = **1**,
      `sha256: 542da14f8aceef7d3d1b8dfbd7801cd78f9a1c4e0d9b8d2940350145d0961703` ×3.
      **This hash does NOT match Rock 5B+ Run-1's recorded 1080p hash
      (`c5925a7e…bbb00`)**, even though Orange Pi's own three repeats at this
      resolution are internally consistent (unique = 1) — which is what this leg
      actually tests, and that holds. The most likely explanation is a minor
      difference in the exact `num-buffers`/`framerate` parameters used for this
      specific sub-leg between the two runs; the raw evidence does not print Rock's
      original 1080p invocation verbatim to compare against. This is reported
      honestly rather than hidden: every OTHER comparable leg in this campaign —
      §3e, §4d, §5a, this same leg's 4K half, §5e's fixqp result, §6d's soak, §7d and
      §7g — matched Rock byte-for-byte, so this one divergence is a genuine, isolated
      discrepancy rather than a pattern. It does not weaken the determinism claim:
      determinism here means the *same board* produces the *same bytes* for the
      *same input*, which Orange Pi's own 3-repeat consistency demonstrates; it does
      not require byte-identity across two different boards.
      4K (3840×2160) ×3 → unique hashes = **1**,
      `sha256: b9d44cc08bf44f2276278fc99c64001c010a06e5d506ba616a989d4c7b7d543d` ×3.
      **HASH IDENTICAL TO ROCK 5B+ RUN-1's 5b 4K result.**
- [x] **5c — repeat 5a across a reboot.** Five runs in one boot can share warm
      state. Reboot between two of the runs and confirm the hash still matches.
      **RUN-1 (Rock 5B+): PASS.** After a full reboot into the same slot, the same
      720p60 command produced
      `a0a83eb40247d9850f702ae464d90c7758b921d287e0aaa61f66885e187291b0` ×2 — **identical
      to the pre-reboot hash** — and the 1080p30 command produced
      `c5925a7ece33908563801048226573cbfc2dcb6120c1229243ee31ea870bbb00`, likewise
      identical. All three post-reboot streams also decode clean (§6a method).
      **RUN-3 (Orange Pi 5 Plus): PASS.** Pre-reboot 720p60 hash: `a0a83eb4…`. Board
      rebooted (`sudo reboot`), reconnected after ~230s, booted back into the same
      slot B (`rauc status` confirmed `Booted from: rootfs.1 (B)`,
      `Activated: rootfs.1 (B)`). Post-reboot 720p60 re-run:
      `a0a83eb40247d9850f702ae464d90c7758b921d287e0aaa61f66885e187291b0` — **identical
      to the pre-reboot hash**.
- [x] **5d — repeat 5a under memory pressure**, so the allocator is forced down
      its lower-order paths and the buffer becomes multi-segment. Record how the
      pressure was created and confirm the hash is unchanged.
      **RUN-1 (Rock 5B+): PASS — the strongest single result against R1.** Pressure was
      created with a 6 GiB tmpfs at `/mnt/ballast` filled with a 5,200 MiB zero file
      (`dd if=/dev/zero of=/mnt/ballast/fill bs=1M count=5200`), taking the board from
      `free 7005 MiB / available 7225 MiB` to `free 1770 MiB / available 1995 MiB`
      (used 542 → 5772 MiB). Under that pressure:
      720p60 ×3 → `a0a83eb4…291b0` ×3, **identical to the unpressured baseline**;
      1080p30 → `c5925a7e…bbb00`, **identical to the unpressured baseline**.
      Ballast released afterwards; `CmaFree` was 23,004 kB during the run (i.e. the
      encoder was still not drawing on CMA).
      **RUN-3 (Orange Pi 5 Plus): PASS, scaled to this board's smaller RAM.** The
      board has only 3765 MiB total RAM (smaller than Rock's config), so ballast was
      scaled to **2500 MiB** (vs Rock's 5200 MiB) via tmpfs `dd if=/dev/zero`, taking
      `available` from 3370 MiB to 869 MiB. Under that pressure:
      720p60 ×3 → `a0a83eb4…291b0` ×3 — **identical to the unpressured baseline**;
      1080p → `542da14f…0961703` — **identical to this board's own 5b baseline**
      (i.e. the §5b discrepancy vs. Rock is stable under pressure too, not a
      one-off measurement artifact). `CmaFree` during pressure: 27,040 kB —
      unchanged, still not drawing from CMA.
- [x] **5e — record the encoder settings used**, in full. A determinism claim is
      meaningless without the rate-control mode; note it explicitly (a CBR/VBR
      mode with a time-varying component is not expected to be deterministic and
      would invalidate this leg — use a fixed-QP mode if one is available and say
      which).
      **RUN-1 (Rock 5B+): RECORDED, and the leg was re-run in fixed-QP.** Element
      defaults as reported by `gst-inspect-1.0 mpph264enc`:
      `rc-mode` = **`cbr`** (enum default 1; available: `0 vbr`, `1 cbr`, `2 fixqp`),
      `qp-init` = 26 (range 0–51), `profile` = `high` (100), `level` = `4` (40),
      `header-mode` = `first-frame`, `bps`/`bps-max`/`bps-min` = 0 (auto), `rotation` = 0.
      Because this leg warns that a CBR result may not be a valid determinism claim,
      §5a/§5b were **re-run explicitly with `rc-mode=fixqp qp-init=26`** — a fixed-QP
      mode does exist and is enum value 2. Both modes gave a single unique hash
      (CBR 720p `a0a83eb4…`, fixqp 720p `c53db770…`, fixqp 1080p `d320d576…`), and
      CABAC remained on in fixqp (`entropy_coding_mode_flag = 1`). The determinism
      conclusion therefore does not rest on the CBR runs alone.
      **RUN-3 (Orange Pi 5 Plus): RECORDED, IDENTICAL DEFAULTS, fixqp HASH MATCHES
      ROCK.** Element defaults via `gst-inspect-1.0 mpph264enc`: `rc-mode` default 1
      (`cbr`), `qp-init` default 26, `profile` default 100 (`high`), `level` default
      40 (`4`), `header-mode` default 0 (`first-frame`), `bps`/`bps-max`/`bps-min`
      default 0 (auto), `rotation` default 0 — **IDENTICAL defaults to Rock 5B+**.
      Re-run with `rc-mode=fixqp qp-init=26`, 720p ×2:
      `sha256: c53db7706e9472f091b6159c033fb75c6ce937ed0bef494cdf1f8c87a771b545` ×2,
      unique hashes = **1** — **HASH IDENTICAL TO ROCK 5B+ RUN-1's fixqp result.**
      CABAC confirmed still on (`entropy_coding_mode_flag = 1` via `ffmpeg …
      -bsf:v trace_headers`).

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
      **RUN-1 (Rock 5B+): PASS.** Exactly this command produced **no output at all**
      and exit `0`.
      **RUN-3 (Orange Pi 5 Plus): PASS.** 10 files (det-1, q1080-1, q4k-1
      [regenerated post-reboot with hashes re-verified identical to pre-reboot
      originals — the reboot cleared `/tmp` so these three were regenerated fresh
      and their hashes independently re-confirmed before decode-testing], pr-1,
      mp-1/2/3, mp1080, fixqp-1/2) decoded with
      `ffmpeg -err_detect explode -i <file> -f null -`. **ALL CLEAN, 0 errors, 0
      output.**
- [x] **6b — CABAC is actually in use**, so 6a is testing what it claims to:
      ```bash
      mediainfo --Inform="Video;%Format_Settings_CABAC%" /tmp/det-1.h264   # expect Yes
      # fallback if mediainfo is unavailable:
      ffmpeg -hide_banner -loglevel trace -i /tmp/det-1.h264 -f null - 2>&1 \
        | grep -i -m1 'cabac'
      ```
      If the encoder is emitting CAVLC, this leg does not exercise the reported
      failure and must be re-run with CABAC forced.
      **RUN-1 (Rock 5B+): PASS.** `mediainfo` is not in the production image and the
      documented `-loglevel trace` fallback surfaced nothing, so the authoritative
      bitstream field was read directly with ffmpeg's `trace_headers` bitstream filter:
      ```
      $ ffmpeg -loglevel debug -i det-1.h264 -c copy -bsf:v trace_headers -f null -
      [trace_headers] 10  entropy_coding_mode_flag  1 = 1
      [trace_headers] 52  cabac_alignment_one_bit   1 = 1
      ```
      `entropy_coding_mode_flag = 1` **is** CABAC (0 would be CAVLC), and
      `cabac_alignment_one_bit` appears per slice. `ffprobe` confirms `profile=High`.
      Also verified still set in the `fixqp` runs. So 6a/6c/6d exercise the reported
      failure mode.
- [x] **6c — decode every run from §5, not just one.** All five, all resolutions.
      **RUN-1 (Rock 5B+): PASS.** All streams decoded with
      `ffmpeg -loglevel error -err_detect explode … -f null -`; every one produced empty
      output: `det-1..5` (720p60 ×5), `q3e` (1080p), `q4d` (4K), the three
      memory-pressure `mp-1..3`, the post-reboot `pr-1`, `pr-2`, `pr1080`, the five
      `fixqp` streams, and both dual-core outputs `c0`/`c1`. **CLEAN** in every case.
      **RUN-3 (Orange Pi 5 Plus): PASS.** Covered by the same 6a batch above — all 10
      files, spanning §5's repeats and resolutions, decoded clean.
- [x] **6d — a long soak decodes clean.** Encode ≥ 10 minutes of continuous video
      and decode the whole thing. The reported failure was intermittent; a 60-frame
      clip is not a sample.
      **RUN-1 (Rock 5B+): PASS.** 18,000 frames at 1920×1080/30 fps = **600 s (10 min)**
      of video, encoded in 1 m 15 s wall time to `soak.h264`, **583,117,763 bytes**.
      `ffprobe -count_frames` → `nb_read_frames=18000` (every frame present). Full-file
      decode with `-err_detect explode` → **no output**, exit `0`. Afterwards:
      guardrail clean, no IOMMU page faults, `tainted` still `0`, core-0 IRQ count
      24,086.
      **RUN-3 (Orange Pi 5 Plus): PASS.** 10-minute soak, 18,000 frames at
      1920×1080/30fps:
      ```
      real 1m14.768s (Rock's Run-1: 1m15s — essentially identical wall time)
      -rw-r--r-- 1 ceralive ceralive 583117763 /tmp/soak.h264
      ```
      **583,117,763 bytes — BYTE-FOR-BYTE IDENTICAL to Rock 5B+ Run-1's soak
      result.** `ffprobe -count_frames` → `nb_read_frames=18000` (every frame
      present). Full decode with `-err_detect explode` → exit 0, no output (clean).
      Post-soak: `dmesg | grep -i guardrail` → clean. `/proc/sys/kernel/tainted` →
      `0`. `/proc/interrupts` `rkvenc0` → 18,599 (core 0 did essentially all the
      soak's work, core 1 still near-zero at this point — expected, single-session
      dispatch goes to the first idle core, exactly as this leg's own text states).
- [x] **6e — pixel-level sanity, not just parse-level.** Decode to raw and eyeball
      or PSNR-compare against the source pattern. A stream can parse cleanly and
      still contain visibly corrupted macroblocks, which is exactly what a stale
      cache line produces.
      **RUN-1 (Rock 5B+): PASS.** The same 30-frame 720p source was tee'd to raw NV12
      and to the encoder, the stream decoded back to raw NV12 (both files exactly
      41,472,000 B = 30 × 1280 × 720 × 1.5), and compared:
      ```
      PSNR y:32.356764 u:59.434370 v:59.732026 average:34.113563 min:32.495576 max:43.371576
      SSIM Y:0.993930 U:0.999875 V:0.999854 All:0.995908 (23.880779)
      ```
      Consistent with ordinary lossy encoding at the default QP. The
      **`min` PSNR of 32.50 against an average of 34.11** is the load-bearing number
      here: a stale cache line would show up as one or more outlier frames dragging the
      minimum far below the mean, and no such frame exists.
      **RUN-3 (Orange Pi 5 Plus): PASS.** Same 30-frame 720p smpte source tee'd to raw
      NV12 and to the encoder, decoded back to raw NV12:
      ```
      PSNR y:33.155511 u:59.490325 v:59.926805 average:34.911618 min:33.292084 max:43.371576
      SSIM Y:0.994890 U:0.999881 V:0.999855 All:0.996549
      ```
      Both raw files exactly 41,472,000 B (= 30 × 1280 × 720 × 1.5), matching the
      expected NV12 frame math and Rock's own file-size check. `min` PSNR (33.29)
      close to average (34.91) — no outlier frame, consistent with ordinary lossy
      encoding, no stale-cache corruption signature.
- [x] **6f — concurrent CPU memory pressure does not corrupt output.** Run §6d
      while something else is churning memory. The cache-alias risk in §Open
      risks is most likely to surface here, if it surfaces at all.
      **RUN-1 (Rock 5B+): PASS, with a scope note.** Under the §5d ballast (available
      RAM 7225 → 1995 MiB) the encodes were both byte-identical to the unpressured
      baselines **and** decoded clean (`mp-1`, `mp-2`, `mp-3`, plus 1080p — all CLEAN,
      guardrail clean, `tainted` 0).       **Scope note:** the pressure was applied to the
      §5a/§5b-sized encodes, not to the full 10-minute §6d soak; a future run should
      combine the ballast with the soak to exercise the longest window under pressure.
      **RUN-3 (Orange Pi 5 Plus): PASS, same scope note as Rock's own Run-1.** Covered
      by 5d's memory-pressure encodes decoding clean in 6a/6c (`mp-1/2/3`, `mp1080`
      all included in the clean-decode batch above). As on Rock, the pressure was
      applied to the short determinism clips, not combined with the full §6d soak.

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
      **RUN-1 (Rock 5B+): PASS.** All four devices present and all four bound to the
      `rkvenc` driver:
      ```
      /sys/bus/platform/devices: fdbd0000.rkvenc-core  fdbe0000.rkvenc-core  mpp-srv  rkvenc-ccu
      /sys/bus/platform/drivers/rkvenc/ -> fdbd0000.rkvenc-core, fdbe0000.rkvenc-core, mpp-srv, rkvenc-ccu
      crw-rw---- 1 root video 508, 0 /dev/mpp_service
      ```
      Re-verified identically after the §5c reboot.
      **RUN-3 (Orange Pi 5 Plus): PASS.** `ls /sys/bus/platform/devices | grep -iE
      'rkvenc|mpp'` → `fdbd0000.rkvenc-core`, `fdbe0000.rkvenc-core`, `mpp-srv`,
      `rkvenc-ccu` — all four bound. `/dev/mpp_service` present,
      `crw-rw---- root video 237,0`.
- [x] **7b — both IOMMUs bound.** `fdbdf000` and `fdbef000`:
      ```bash
      ls /sys/bus/platform/devices | grep -iE 'fdbdf000|fdbef000'
      dmesg | grep -i 'rk_iommu\|rockchip-iommu'
      ```
      **RUN-1 (Rock 5B+): PASS.** Both present — `fdbdf000.iommu`, `fdbef000.iommu` —
      and each core sits in its own IOMMU group:
      ```
      platform fdbd0000.rkvenc-core: Adding to iommu group 13
      platform fdbe0000.rkvenc-core: Adding to iommu group 14
      ```
      *Naming note:* this kernel logs no `rk_iommu`/`rockchip-iommu` prefix; the RK3588
      IOMMU lines appear under the generic `iommu:` prefix plus `arm-smmu-v3
      fc900000.iommu` (see §10a-1 for the full capture).
      **RUN-3 (Orange Pi 5 Plus): PASS.** `dmesg | grep -i 'adding to iommu group'` →
      `fdbd0000.rkvenc-core` group 12, `fdbe0000.rkvenc-core` group 13 — distinct
      IOMMU groups (different group numbers than Rock's 13/14, which is expected on a
      different SoC instance's group enumeration; what matters is each core has its
      own group).
- [x] **7c — the CCU counted two cores.** The CCU increments `core_num` once per
      core probe; confirm from the driver's own log output that it saw **2**, not
      1. Record the exact line.
      **RUN-1 (Rock 5B+): PASS.** Exact lines, both boots:
      ```
      rkvenc rkvenc-ccu: rkvenc ccu probe success
      rkvenc fdbd0000.rkvenc-core: attach ccu as core 0 [main]
      rkvenc fdbd0000.rkvenc-core: rkvenc core 0 probe success (hw_id: 50603312)
      rkvenc fdbe0000.rkvenc-core: attach ccu as core 1 [secondary, active]
      rkvenc fdbe0000.rkvenc-core: rkvenc core 1 probe success (hw_id: 50603312)
      ```
      Two distinct `attach ccu as core N` lines (0 `[main]`, 1 `[secondary, active]`),
      i.e. the CCU saw 2.
      **RUN-3 (Orange Pi 5 Plus): PASS.** Exact lines:
      ```
      rkvenc mpp-srv: mpp_service probe success
      rkvenc rkvenc-ccu: rkvenc ccu probe success
      rkvenc fdbd0000.rkvenc-core: attach ccu as core 0 [main]
      rkvenc fdbd0000.rkvenc-core: rkvenc core 0 probe success (hw_id: 50603312)
      rkvenc fdbe0000.rkvenc-core: attach ccu as core 1 [secondary, active]
      rkvenc fdbe0000.rkvenc-core: rkvenc core 1 probe success (hw_id: 50603312)
      ```
      **IDENTICAL structure to Rock 5B+'s Run-1 log (same `hw_id` too: 50603312).**
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
      **RUN-1 (Rock 5B+): PASS — and this is the leg R4 exists for.** Both counts
      advanced, and core 1 went from **never having done any work** to doing some:
      ```
      before:  110: 600  fdbd0000.rkvenc-core     114:   0  fdbe0000.rkvenc-core
      after:   110: 1591 fdbd0000.rkvenc-core     114: 209  fdbe0000.rkvenc-core
      ```
      Core 0 `600 → 1591` (+991), core 1 **`0 → 209`**. Note the `before` snapshot
      confirms the expectation in the leg text: every preceding single-session encode
      had landed on core 0 only.
      **RUN-3 (Orange Pi 5 Plus): PASS — both cores advanced.** Two concurrent
      sessions (smpte 1080p/600 frames + ball 1080p/600 frames):
      ```
      before: fdbd0000 irq=18599  fdbe0000 irq=1
      after:  fdbd0000 irq=19637  fdbe0000 irq=163
      ```
      Core 0 +1038, core 1 +162 — **BOTH advanced**.
      ```
      c0.h264 (smpte): 19,206,933 bytes — BYTE-FOR-BYTE IDENTICAL to Rock Run-1's 7f result
      c1.h264 (ball):    186,535 bytes — BYTE-FOR-BYTE IDENTICAL to Rock Run-1's 7f result
      ```
- [x] **7e — per-core `clk_core` enable state is observable and correct.**
      ```bash
      grep -iE 'rkvenc' /sys/kernel/debug/clk/clk_summary
      ```
      Record `enable_cnt`, `prepare_cnt` and `rate` for **each** core's
      `aclk_vcodec` / `hclk_vcodec` / `clk_core`, three times: idle, one session
      running, two sessions running. Expect the idle core's `clk_core` enable
      count to be 0 at idle and to rise only when that core is given work. (`debugfs`
      is mounted on the shipped image — confirmed in `image-building-pipeline`.)
      **RUN-1 (Rock 5B+): PASS — all three samples, plus a return-to-idle fourth.**
      `enable`/`prepare`/`rate`:
      | sample | `clk_rkvenc0_core` | `clk_rkvenc1_core` | `aclk_rkvenc0` | `aclk_rkvenc1` | `hclk_rkvenc0` | `hclk_rkvenc1` |
      |---|---|---|---|---|---|---|
      | IDLE | 0/1 @786431998 | **0**/1 @786431998 | 1/6 @500 MHz | 0/4 @500 MHz | 1/6 @198 MHz | 0/4 @198 MHz |
      | ONE SESSION | 2/2 | **0**/1 | 4/7 | 0/4 | 4/7 | 0/4 |
      | TWO SESSIONS | 1/1 | **1**/1 | 3/6 | **2**/4 | 3/6 | **2**/4 |
      | IDLE AGAIN | 1/1 | **0**/1 | 3/6 | 0/4 | 3/6 | 0/4 |
      Exactly the expected behaviour: core 1's `clk_core` enable count is **0 at idle**,
      **still 0 with one session running**,       **rises to 1 only when a second session
      forces work onto it**, and returns to 0 afterwards. Rates are stable at
      786,431,998 Hz (`clk_core`), 500 MHz (`aclk`) and 198 MHz (`hclk`).
      **RUN-3 (Orange Pi 5 Plus): PASS — same pattern, same rate.** Four samples via
      `/sys/kernel/debug/clk/clk_summary`, `clk_rkvenc{0,1}_core` enable/prepare
      counts (all rates stable at 786,431,998 Hz, matching Rock exactly):
      ```
      IDLE:         core0 enable=0 prepare=1   core1 enable=0 prepare=1
      ONE SESSION:  core0 enable=2 prepare=2   core1 enable=0 prepare=1
      TWO SESSIONS: core0 enable=1 prepare=1   core1 enable=1 prepare=1
      IDLE AGAIN:   core0 enable=1 prepare=1   core1 enable=0 prepare=1
      ```
      **IDENTICAL BEHAVIOURAL PATTERN to Rock 5B+ Run-1** (core 1 stays 0 until a
      second session forces it, then returns to 0).
- [x] **7f — both outputs from 7d are correct**, per §6a. A dual-core run that
      produces two streams and corrupts one is the failure mode this leg exists
      for.
      **RUN-1 (Rock 5B+): PASS.** Both files decode clean with `-err_detect explode`:
      `c0.h264` (19,206,933 B, `pattern=smpte`) → CLEAN;
      `c1.h264` (186,535 B, `pattern=ball`) → CLEAN.
      The large size difference is content, not corruption — the leg's own commands
      specify two *different* patterns.
      **RUN-3 (Orange Pi 5 Plus): PASS.** Both 7d outputs decoded clean (`ffmpeg
      -err_detect explode`, both exit 0, no output).
- [x] **7g — dual-core determinism.** Re-run 7d five times; each output file's
      hash must be stable across runs, per §5a. Core assignment may vary between
      runs, so if the hashes differ, first establish whether the *same* core
      produced the same bytes before concluding non-determinism.
      **RUN-1 (Rock 5B+): PASS.** Five concurrent pairs at 1080p/300 frames:
      smpte stream → unique hashes = **1**
      (`7a81c3203e277f4251e889fa524acbc2d49e40f2db95b06697144512cbd818d3` ×5);
      ball stream → unique hashes = **1**
      (`4da1526947b3d758b2081377a395c6b92b2711040eef796060e91711203213c7` ×5).
      Both cores were exercised across the runs (IRQ totals afterwards: core 0 5,866,
      core 1 734), so the stability holds *despite* varying core assignment — the
      disambiguation this leg asks for was therefore not needed.
      **RUN-3 (Orange Pi 5 Plus): PASS.** 5× repeat of 7d, at 300 frames per stream
      instead of 600:
      ```
      smpte: sha256 7a81c3203e277f4251e889fa524acbc2d49e40f2db95b06697144512cbd818d3  x5, unique=1
      ball:  sha256 4da1526947b3d758b2081377a395c6b92b2711040eef796060e91711203213c7  x5, unique=1
      ```
      **BOTH HASHES BYTE-FOR-BYTE IDENTICAL TO ROCK 5B+ RUN-1's 7g result.** IRQ
      totals across the 5 runs: core 0 +2572, core 1 +428 — both cores genuinely
      exercised across the repeats.

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
      **RUN-1, board = Radxa Rock 5B+: PASS (card existence only).** `/proc/asound/cards`
      lists **five** cards, and card 4 is the HDMI-RX one:
      ```
       0 [usbaudio     ]: USB-Audio - RØDE HDMI to USB-C
       1 [rk3588es8316 ]: rk3588-es8316 - rk3588-es8316
       2 [hdmi0        ]: simple-card - hdmi0
       3 [hdmi1        ]: simple-card - hdmi1
       4 [hdmirx       ]: simple-card - hdmirx
      ```
      `/proc/asound/hdmirx/` contains `pcm0c` — a **capture** PCM — plus `eld#0`.
      This is `0006` (the DT half) working: cards 2/3 are the HDMI **transmitters**
      and card 4 is the fifth, new card the fix was written to add.
      *Substitution recorded:* `arecord -l` was unavailable (`alsa-utils` not in the
      production image); `/proc/asound/cards` + `/proc/asound/hdmirx/` were used instead.
      **This leg is card existence ONLY — it is not a claim that audio captures; see 8c.**
- [ ] **8b — Orange Pi 5 Plus: same check, recorded separately.** These are two
      results, never one. The upstream alternative to `0006` was declined
      precisely because it enables the card on Orange Pi 5 Plus only.
      **RUN-1: NOT RUN — no Orange Pi 5 Plus available this session.** Given why `0006`
      was chosen over the upstream alternative, this row is the important one and it
      remains open.
- [ ] **8c — audio actually captures**, with the HDMI source device **named**:
      ```bash
      arecord -D hw:<card>,0 -f S16_LE -r 48000 -c 2 -d 10 /tmp/hdmirx.wav
      ```
      Record: board, source device make/model, source output resolution and
      framerate, source audio sample rate and channel count.
      **RUN-1: NOT RUN — hardware source unavailable this session.** No HDMI source was
      connected to the board's HDMI-IN port (`v4l2-ctl -d /dev/hdmirx --get-dv-timings`
      reports the no-signal default 640×480/800×525). `alsa-utils` is also absent from
      the production image, so `arecord` does not exist. **Both** blockers must be
      cleared for this leg: a real HDMI source *and* a DEBUG image or `debug-toolset`.
- [ ] **8d — the captured audio is not silence.** Check the RMS level, not just
      the file size. A zero-filled WAV is the most common false pass here.
      **RUN-1: NOT RUN — depends on 8c, hardware source unavailable this session.**
- [ ] **8e — capture survives a cable replug** (this is what `0003` guards):
      unplug, wait, replug, capture again. Record whether the card and the stream
      recover without a reboot.
      **RUN-1: NOT RUN — hardware source unavailable this session, and the session was
      remote with no physical access to replug a cable.**
- [x] **8f — the codec is bound AND a card exists**, not just the former:
      ```bash
      ls /sys/devices/platform/fdee0000.hdmi_receiver/
      ```
      A bound `hdmi-audio-codec.N.auto` with no card in 8a/8b is the exact silent
      failure state that `0006` was written to remove.
      **RUN-1, board = Radxa Rock 5B+: PASS.** The codec is bound —
      `/sys/devices/platform/fdee0000.hdmi_receiver/hdmi-audio-codec.5.auto` — **and**
      card 4 `hdmirx` exists (8a). So the silent-failure state `0006` targets is
      **not** present on this board. The same directory also carries `cec0` and
      `video4linux`; the V4L2 side reports `Driver name: snps_hdmirx`,
      `Bus info: platform:fdee0000.hdmi_receiver`, `Driver version: 7.1.7`, with
      `/dev/hdmi-in` and `/dev/hdmirx` both symlinked to `video6`.
- [x] **8g — every audio claim in this repository's docs names its hardware.**
      Sweep `README.md`, `AGENTS.md`, `EVAL-0005-AUDIO.md` and this file after the
      run; any sentence that says "HDMI-RX audio works" without a board name and a
      source device is to be rewritten or deleted.
      **RUN-1: PASS — swept, nothing to rewrite.** `README.md`, `AGENTS.md`,
      `docs/EVAL-0005-AUDIO.md` and this file were searched for claims of the form
      "audio works / audio capture works / audio confirmed / audio validated". **No
      unqualified claim exists** — the only hits are structural or analytical
      (`AGENTS.md` line 71 routes to why `0006` is needed; `EVAL-0005-AUDIO.md` line 100
      describes `hdmirx_plugout()` behaviour). The two new claims added by this run
      (8a, 8f) both name the board explicitly and are both scoped to *card existence
      and codec binding*, not to working capture.

---

## 9. HDMI-RX EDID and 4K60 — checks B1–B7

Moved here from [`EVAL-0002-EDID.md`](EVAL-0002-EDID.md) § *"Requires board
validation at 4K60"*, which parked them pending this document. **B5 is the
retirement precondition for `0002`** — until it is answered on hardware, `0002`
is not a retirement candidate.

**RUN-1: NONE OF B1–B7 WERE RUN — every one needs a 4K60-capable HDMI *source*
attached to the board's HDMI-IN port, and no HDMI source of any kind was connected
this session.** `v4l2-ctl -d /dev/hdmirx --get-dv-timings` reported the no-signal
default (640×480, total 800×525), confirming no source was present. `v4l2-ctl` itself
IS available in the production image, so these legs are unblocked by tooling — they
are blocked purely on physical hardware. **`0002` therefore remains a
non-retirement-candidate.**

- [ ] **B1 — 4K60 EDID is accepted and re-read.** Write an EDID advertising
      `SCDC_Present = 1`, `Max_TMDS_Char_Rate ≥ 594 MHz` and VIC 97 via
      `VIDIOC_S_EDID` (`v4l2-ctl --set-edid=file=...`), then confirm the *source*
      re-reads it and offers 2160p60.
      **RUN-1: NOT RUN — no HDMI source attached (needs a source that re-reads EDID).**
- [ ] **B2 — the SCDC TMDS ratio flips to 1/40 and the receiver locks at
      594 MHz.** Capture `signal lock ok, i:%d` with the driver at `debug=1` and
      **record the iteration count** — it is the input to B3 and B4.
      **RUN-1: NOT RUN — no HDMI source attached (needs a real 4K60 signal to lock).**
- [ ] **B3 — is the ~147 ms consecutive-stability window the right threshold at
      4K60?** Answer from B2's measured iteration counts, not from the source.
      **RUN-1: NOT RUN — depends on B2's measurements.**
- [ ] **B4 — is the ~4.2 s ceiling enough, and does the `i == 300` PHY re-init
      actually recover a PHY that latched the pre-flip ratio?** Force the case if
      it does not occur naturally.
      **RUN-1: NOT RUN — depends on B2; needs a 4K60 source.**
- [ ] **B5 — with the 150 ms HPD hold already in the base (`7dd27810eea0`), is
      `0002`'s sequence still required for a 4K60 EDID to be re-read?** Run with
      and without `0002` and compare. **This is the `0002` retire trigger.**
      **RUN-1: NOT RUN — needs a 4K60 source AND a second image built without `0002`.
      `0002` remains NOT a retirement candidate.**
- [ ] **B6 — is the 160 MiB `hdmi_receiver_cma` pool right for a realistic vb2
      queue depth at 4K60, on BOTH boards?** The DT comment's 66 MB figure is a
      two-frame number.
      **RUN-1: NOT RUN — needs a 4K60 source, and is a two-board question (see R8);
      only a Rock 5B+ was available.** The pool itself was confirmed assigned at boot:
      `snps_hdmirx fdee0000.hdmi_receiver: assigned reserved memory node hdmi-receiver-cma`.
- [ ] **B7 — is the `msleep(500)` after the DMA reset over-conservative at
      4K60?** Measure the actual settle time before changing anything.
      **RUN-1: NOT RUN — needs a 4K60 source to measure a real settle time.**

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
      **RUN-1 (Rock 5B+): PASS, with a naming correction.** This kernel emits **no**
      `rk_iommu`/`rockchip-iommu` prefixed lines at all — the grep as written returns
      nothing, which is a false negative rather than a missing driver. The IOMMU lines
      appear under the generic `iommu:` prefix and the SMMU's own device name. Every
      IOMMU line from boot:
      ```
      iommu: Default domain type: Translated
      iommu: DMA domain TLB invalidation policy: strict mode
      arm-smmu-v3 fc900000.iommu: oas 48-bit (features 0x001c1eaf)
      arm-smmu-v3 fc900000.iommu: allocated 65536 entries for cmdq
      arm-smmu-v3 fc900000.iommu: allocated 32768 entries for evtq
      arm-smmu-v3 fc900000.iommu: msi_domain absent - falling back to wired irqs
      platform fdb50000.video-codec: Adding to iommu group 0
      platform fdba0000.video-codec: Adding to iommu group 1
      platform fdba4000.video-codec: Adding to iommu group 2
      platform fdba8000.video-codec: Adding to iommu group 3
      platform fdbac000.video-codec: Adding to iommu group 4
      platform fdd90000.vop:         Adding to iommu group 5
      pci 0000:00:00.0:              Adding to iommu group 6
      pci 0001:10:00.0:              Adding to iommu group 7
      platform fdab0000.npu:         Adding to iommu group 8
      platform fdac0000.npu:         Adding to iommu group 9
      platform fdad0000.npu:         Adding to iommu group 10
      platform fdc38000.video-codec: Adding to iommu group 11
      platform fdc40000.video-codec: Adding to iommu group 12
      platform fdbd0000.rkvenc-core: Adding to iommu group 13
      platform fdbe0000.rkvenc-core: Adding to iommu group 14
      pci 0004:40:00.0 / 0004:41:00.0: Adding to iommu group 15
      pci 0002:20:00.0 / 0002:21:00.0: Adding to iommu group 16
      ```
      Both rkvenc cores are IOMMU-backed (groups 13 and 14), which is the
      precondition for `0008`/`0009` to mean anything. **Suggested amendment:** this
      leg's grep should be widened to `-iE 'iommu'` for the mainline naming.
- [x] **10a-2 — no page faults during a sustained encode soak.**
      ```bash
      dmesg | grep -iE 'iommu.*(page fault|Page Fault|status)'   # expect NOTHING
      ```
      Run §6d's 10-minute soak and check after.
      **RUN-1 (Rock 5B+): PASS.** Checked immediately after the §6d 10-minute /
      18,000-frame soak, and again after the dual-core and memory-pressure batches:
      **no matches** every time. `tainted` remained `0`.
- [ ] **10a-3 — no VOP stall / black screen** across a soak with display output
      active *and* encode running simultaneously. This is the reported symptom;
      run both engines at once or the leg does not exercise the race.
      **RUN-1: NOT RUN — no display attached, so display output could not be active.**
      The boot log's 16 × `dwhdmiqp-rockchip fde80000.hdmi: i2c read error` lines
      independently confirm no monitor was connected to the HDMI **output**. The soak
      therefore ran encode-only and did **not** exercise the VOP-vs-encode race this
      leg exists for. `fdd90000.vop` is present and IOMMU group 5 (see 10a-1), so the
      leg is blocked purely on a physical display.
- [ ] **10a-4 — no RGA3 hang** across the same soak, if RGA is exercised at all
      on the image under test. If RGA is not reachable on the `edge` track (see
      the pipeline's `librga` / `/dev/rga` note), record that and mark this
      sub-leg *not exercised* rather than passed.
      **RUN-1: NOT EXERCISED — recorded as this leg instructs.** RGA was not driven by
      any pipeline in this run, and per the pipeline's own `librga` / `/dev/rga` note
      the vendor RGA char device is not reachable on the `edge` track (mainline exposes
      RGA only as a V4L2 M2M node). Marked *not exercised*, explicitly **not** passed.

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
      **RUN-1: correctly left unticked (N/A leg, rule 3).** Incidentally observed on the
      Rock 5B+: the `rk3588es8316` card (card 1) is present and the board's analog
      audio path is intact — consistent with not having imported the regressing series.

### 10c. PCIe system suspend/resume — **N/A, not imported** (T13 skipped)

- [ ] **10c — N/A.** Not imported. The v5 posting is 6 prerequisites deep (three
      times the ceiling), its payload `7/8` does not apply to `v7.1.7` even with
      `1/8`–`6/8` first, and Rockchip's own PCIe maintainer objected that it puts
      host and device into D3cold unconditionally, which does not meet NVMe's
      requirement — on hardware Rock 5B+ has (an M.2 NVMe slot). **Nothing was
      imported, so there is no suspend/resume behaviour of ours to qualify.**
      Ordinary system suspend/resume on the stock `v7.1.7` PCIe code is out of
      this series' scope.
      **RUN-1: correctly left unticked (N/A leg, rule 3).** No suspend/resume was
      exercised.

### 10d. V4L2 hardware-usage stats via `fdinfo` — **N/A, not imported** (T13 skipped)

- [ ] **10d — N/A.** Not imported. It was the only T13 candidate that passed
      mechanically (applies to bare `v7.1.7` with no fuzz, prerequisite depth
      exactly 2), and it was declined **on merit**: its payload publishes five
      `/proc/<pid>/fdinfo/<fd>` keys, i.e. userspace ABI, and all five had already
      been agreed in-thread to be renamed. **No `media-*` fdinfo keys should exist
      on the board** — if any appear, something other than this series put them
      there and that is worth investigating.
      **RUN-1: correctly left unticked (N/A leg, rule 3) — negative observation
      recorded.** A sweep of `/proc/*/fdinfo/*` across the running process set found
      **no `media-*` keys**, as expected. Nothing to investigate.

### 10e. V4L2 stateless-codec tracepoints — **N/A, not imported** (T13 skipped)

- [ ] **10e — N/A.** Not imported. Prerequisite depth 4, over the ceiling, and the
      tracing maintainer filed an unanswered design objection with no respin in
      ~6 months. **No `v4l2_hw_run` / `v4l2_hw_done` tracepoints should exist**;
      `ls /sys/kernel/debug/tracing/events/v4l2/` will show only the base tree's.
      Nothing to qualify.
      **RUN-1: correctly left unticked (N/A leg, rule 3) — negative observation
      recorded.** No `hw_run` / `hw_done` entries under
      `/sys/kernel/debug/tracing/events/v4l2/`, as expected.

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
      **RUN-1: correctly left unticked (N/A leg, rule 3) — negative observation
      recorded.** `find /sys/kernel/debug/dri -iname '*scdc*'` returned nothing, as
      expected.

---

## 11. A kernel-side task failure does NOT reach the application (MPP-layer characteristic)

**This is a userspace characteristic of the shipped MPP stack, not a kernel defect,
and nothing in this repository can fix it.** It is written down here because the
fault-injection QA used to assert on `gst-launch-1.0`'s exit status, and that
assertion was measuring `librockchip-mpp`, not the driver. The measurement below is
what retired that assertion; what replaced it is at the end of this section.

Measured on a Rock 5B+ (`7.1.7-ceralive-rk3588-test`, KASAN + `PROVE_LOCKING`) with
`librockchip-mpp1 1.5.0-1`, `gstreamer1.0-rockchip1 1.14-4`
(`libgstrockchipmpp.so` 1.14.4), arming `fail_clock_enable_once` and running the
standard 60-frame `videotestsrc ! mpph264enc ! h264parse ! filesink` probe.

**The kernel does its job, exactly once.** With `/sys/module/rkvenc/parameters/debug`
set to `0x20` (`DEBUG_FUNCTION`), a fault-armed 60-frame encode logs:

| counter | no fault | fault armed |
|---|---|---|
| `rkvenc_hw_run` **enter** | 60 | **60** |
| `rkvenc_hw_run` **leave** (success only) | 60 | **59** |
| `hw_run failed` | 0 | **1** |
| `wait result ret -19` (`-ENODEV` to userspace) | 0 | **1** |
| output bytes | 1854524 | 1697683 |

**Sixty dispatches for sixty frames.** The failed frame is dispatched once, fails
once, is reported once, and is **never retried** — not by the driver (the only
insertion into `queue->pending_list` is in `rkvenc_dev_ioctl()`, and the worker
`list_del_init()`s a task before dispatching it and never re-adds it) and not by
MPP (a 61st submission would be a 61st `ioctl(2)`, and there isn't one).

**What userspace does with the `-ENODEV` is timing-dependent.** Uninstrumented —
i.e. the way a real operator runs it — the result was `rc=0` with a **1,697,683-byte**
stream, 5/5 identical, against a canonical **1,854,524**. The encode "succeeds" and
is 8.5 % short. Adding kernel logging slows the ioctl path and MPP instead aborts
(`rc=134`, SIGABRT) with a truncated stream; at `debug=0x30` that was 4/5 aborts.
So `rc=134` and `rc=0` are two faces of one race inside MPP, and **neither is
evidence about the driver**.

> **Do not read an older `rc=134` as "the error propagated correctly."** The
> attempt-7 run that recorded it also carried a live `use-after-free` in
> `rkvenc_task_worker_default()`; the abort is at least as consistent with that
> corruption as with clean error reporting.

**Consequence for QA.** `tests/rkvenc-fault-qa.sh`'s `fail-clock-enable` case used to
assert that `gst-launch-1.0` exits non-zero (`qa_encode_expect_failure`). On this MPP
that assertion is **flaky by construction** and failed deterministically. The honest
assertion for a *kernel* patch series is kernel-side and stream-side:

1. `fail_clock_enable_once_consumed` incremented exactly once (already asserted);
2. the kernel logged `hw_run failed: -5` **and** `wait result ret -19` — the driver
   detected the fault and reported it to its caller; and
3. the fault-armed stream is **measurably shorter** than the canonical no-fault
   stream — the frame really was lost rather than silently substituted.

**This change HAS now been made** (run 2). It was an orchestrator decision rather than
a side-effect of a driver fix, because it alters what a released QA gate asserts, and
it was taken deliberately on the strength of the measurement above.
`qa_encode_expect_failure()` now measures its output **before** deleting it — the `rm`
used to destroy the one number that distinguishes "the frame was lost" from "nothing
happened" — screens the kernel log between a `qa_dmesg_mark` taken either side of the
encode for `hw_run failed: -<errno>` and `wait result ret -19` **exactly once each**,
and compares the byte count against `QA_ENCODE_CANONICAL_BYTES` (1854524, the §3e
figure, carried with the 60-frame count it was measured at). The exit status is still
printed in the transcript, labelled as a diagnostic, and is no longer the gate.

The replacement is **stricter**, not laxer, and in two directions at once: the `rc=0`
run measured above now passes, where the old gate failed it; and a run whose kernel
never logged the fault at all now fails, where the old gate would have passed it on any
non-zero exit code — including the attempt-7 `rc=134` that was actually a
`use-after-free`. Both directions, the exactly-once counting, the shorter-but-non-empty
band and the two guards (nothing armed; a frame count the canonical size was not
measured at) are pinned by `tests/rkvenc-fault-qa.sh --self-test`, which reads a
captured log through `QA_DMESG_CMD` the same way the fixture legs read a synthetic
debugfs through `QA_DEBUGFS` — so none of it needs a board.


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

> **RUN-1 status:** not observed on Rock 5B+ across everything that was run — 5×/3×
> byte-identical output at 720p/1080p/4K, identical across a reboot, identical under
> ~5.2 GiB of memory pressure, clean `-err_detect explode` decodes of every stream
> including a 10-minute 18,000-frame soak, and PSNR/SSIM with no outlier frame.
> **This lowers the risk; it does not close it.** R1's own point is that the failure
> is intermittent and time-dependent, so "not seen in one session" is not "cannot
> happen". The strongest single result is §5d (identical bytes under pressure), and
> the biggest remaining gap is that the 10-minute soak was **not** run concurrently
> with memory pressure (see §6f's scope note).

**R2 — an intermittent failure needs a soak, not a smoke test.** The original
report was *intermittent* CABAC failures and *varying* output sizes. A 30-frame
clip that decodes is the single most likely way to declare success incorrectly.
§5 and §6d exist to prevent exactly that.

> **RUN-1 status:** addressed, not merely acknowledged. §6d encoded and decoded a
> full 10 minutes (18,000 frames, 583 MB, all 18,000 frames read back) with
> `-err_detect explode` and produced no error output, and §6b proved CABAC was
> actually in use (`entropy_coding_mode_flag = 1`) so the soak exercised the reported
> failure mode rather than a CAVLC path.

**R3 — a symlink or `mknod` alias would make §2a and §3a pass and everything else
lie.** It is explicitly rejected by the pipeline's KNOWN ISSUE: aliasing the
`system` heap hands MPP cached memory it will not synchronise, and aliasing the
CMA heap caps out below 1080p (32 MiB pool, ~1.9 MiB largest run, ~3.1 MiB needed).
§2b is the check that catches it. If §2a passes and §5 fails, suspect an alias
before suspecting the patch.

> **RUN-1 status:** ruled out on this board, three independent ways. §2b — distinct
> device minors (`250,1` vs `system`'s `250,0`) and a separate `/sys/class/dma_heap/`
> entry, so not a symlink or `mknod` onto `system`. §2f — `CmaFree` did not move while
> 15.2 MB was held from `system-uncached`, while the same allocations from
> `default_cma_region` moved it by exactly that much, so not an alias onto CMA. §2e —
> a 4K (11.87 MiB) allocation succeeded, which the CMA-alias trap could not do.
> And §5 passed rather than failed, which is the corroborating signal this risk
> predicts.

**R4 — dual-core is easy to leave untested.** Every single-session test can pass
on core 0 alone. §7d is the only leg that forces core 1 to do work, and §7g is the
only one that asks whether the two cores agree.

> **RUN-1 status:** exercised, and the risk was real. The IRQ snapshot taken *before*
> §7d showed core 1 at exactly **0** interrupts after every preceding single-session
> encode in this run — i.e. everything up to that point genuinely had run on core 0
> alone. §7d moved core 1 to 209 and §7g showed both streams byte-stable across five
> concurrent pairs.

**R5 — `0009` is `UNVALIDATED` and so is `0008`.** Neither has ever been observed
on a board. Nothing in this repository, its README or its `AGENTS.md` may describe
MPP hardware encode on the `edge` track as working until §2 through §7 are ticked
with transcripts. Compile-and-boot is not qualification.

> **RUN-1 status:** §2 through §7 are now ticked with transcripts **on a Radxa Rock
> 5B+**, with two exceptions that are recorded rather than glossed: **3c/3d** could
> not be made meaningful because MPP printed no internal log lines at any verbosity
> tried, and **4c** is not instrumented (4a+4b is explicitly recorded as the strongest
> available evidence). Neither exception is load-bearing for defect 1, 2 or 3 — 3a/3e
> and 4a/4b/4d carry those.
> **The `UNVALIDATED` markers in [`UPSTREAM-STATUS.md`](UPSTREAM-STATUS.md) were NOT
> cleared by this run, deliberately.** Clearing them is a separate, explicit decision:
> it rewrites the patch-status contract, and §1b/§8b leave the Orange Pi 5 Plus column
> entirely unrun (R8). Treat run 1 as *unblocking* that decision for the Rock 5B+
> evidence, not as having taken it.

**R6 — a `.deb` from this series is not byte-reproducible.** `git am` restamps
committer dates, so two builds of the same source produce different kernel package
hashes. Do not treat a hash difference between builds as evidence of anything;
compare package **contents** instead.

> **RUN-1 status:** no cross-build comparison was made or relied upon. The artifact
> under test was identified by its own bundle SHA-256 (`f55ae8cf…30472`) and by the
> asserted `patches_commit`, not by comparing kernel package hashes between builds.

**R7 — eMMC HS400 negotiation is inconsistent on this kernel** and is a known,
deliberately-unfixed upstream behaviour, not a result of this series. If
`/dev/mmcblk0` does not appear, that is R7, not §1. Do not chase it here.

> **RUN-1 status:** the warning appeared and was correctly *not* chased. Four
> `sdhci-dwcmshc fe2e0000.mmc: Can't reduce the clock below 52MHz in HS200/HS400 mode`
> lines are in `dmesg-err.log`, and on this boot the eMMC nevertheless enumerated
> fully (`mmcblk0` with p1–p4 plus `mmcblk0boot0`/`boot1`). Recorded under §1c as
> pre-existing and attributed to R7, not to this series.

**R8 — the boards are not interchangeable.** Every leg in §1, §8 and §9 is a
two-column result. A finding on Rock 5B+ is not transferable to Orange Pi 5 Plus,
and the HDMI-RX audio history in this repository is the standing proof of that.

> **RUN-1 status:** honoured. Only a Radxa Rock 5B+ was available, so **§1b and §8b
> are unrun and stay unticked**, and every §8/§9 note above names the board
> explicitly. The Orange Pi 5 Plus column of this checklist is entirely open.
> Note also the pipeline's own separate finding that `snps_hdmirx` fails to probe on
> Orange Pi 5 Plus for a TF-A/BL31 reason — so §8b on that board may be blocked by
> firmware before it is blocked by this series.
