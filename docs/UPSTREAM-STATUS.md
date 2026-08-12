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

The series has twenty-one members. `0004` is a deliberate ordinal gap — upstream never
published one — and is not a row here for the same reason it is not a patch.

Six of them (`0013`–`0018`) are **Wave-6 first-party quality patches**: one is test
instrumentation that is absent from every production build, one states an existing
API's failure semantics truthfully rather than fixing a defect, and the other four
repair concrete defects in the code that runs when something goes wrong. All six
have `first-party-no-upstream` status for the same structural reason `0008` does —
they fix the imported `0001`/`0005` drivers, and there is no upstream counterpart of
those drivers to backport a fix from.

`0019` is a **Wave-8 first-party fix** and carries the same `first-party-no-upstream`
status for the same reason, but it is separated from that group by how it was found:
`0013`–`0018` were root-caused by reading the imported drivers, whereas `0019` was
root-caused from a **real Rock 5B+ KASAN+LOCKDEP boot log** captured during a plain,
unfaulted encode. Both of its defects are `0001`'s as imported — neither the `0013`
test hook nor the `0014` teardown work touches the code either one lives in.

`0020` is the second **Wave-8 first-party fix** and was found the same way — on real
hardware, this time by fault injection rather than a plain encode. It differs from
`0019` in what it fixes: `0019` repairs `0001` as imported, whereas `0020` repairs
**`0014`'s own** service lifetime model, which drove a permanent `DEAD` state from a
transient single-core unbind. It therefore retires with `0014`, not with `0001`.

`0021` and `0022` are the third and fourth **Wave-8 first-party fixes**, and they
exist for a reason worth stating plainly: **`0015` and `0016` were marked done
before anything had run on a board, and the first real drill against them failed.**
Both were root-caused from that drill's transcripts. `0021` fixes an
acquire/release asymmetry between `rkvenc_hw_run()` and `rkvenc_task_finish()` that
`0015` made *reachable* — by propagating a clock-enable failure that used to be
discarded — without creating it; the unconditional release is `0001`'s. `0022`
completes `0016`: four of the eight cases in `tests/expected-errno.tsv` still did
not hold on hardware, and reading the same paths to find out why turned up two more
bounds defects of the same shape that no case covers. Neither patch changes a test
expectation. **One drill case, `valid-after-failures`, still fails after both, for a
reason that is neither patch's** — see [§ `0022`](#0022--what-it-fixes-what-it-does-not-and-the-one-case-still-red).

**`0022` was then found broken by hardware and amended in place.** Its first version
fixed the three drill cases it targeted — confirmed on a board — and simultaneously
refused **every** production encode, because the containment test it introduced was
exact and `librockchip-mpp`'s real register write is not exactly contained. A
cold-boot control encode with nothing armed caught it; an A/B one RAUC slot apart
confirmed it. The patch was corrected rather than reverted, since the three fixes it
proved are worth keeping, and the amendment is **host-verified only**. The lesson
generalises beyond this patch and is written down in [§ `0022`](#0022--what-it-fixes-what-it-does-not-and-the-one-case-still-red):
a **cold-boot, no-fault control encode** belongs in every rkvenc UAPI change's
acceptance, not just the fault cases the change was written for.

`0023` is the fifth **Wave-8 first-party fix**, and the run that produced it is the
run that confirmed `0021`: the same board, the same fault case, a clean lock and PM
record — and one `KASAN: use-after-free` in `rkvenc_task_worker_default()`. It is a
lifetime defect, not a locking one. `rkvenc_task_finish()` drops the reference the
core held and `kfree()`s the task when the waiter has already dropped the other one,
and the worker went on reading the pointer afterwards in two places. **Both reads
are `0001`'s as imported**, and no patch between them moved either: `0013` inserts
its delay *before* the finish, `0019` changes only the queue lock types, and `0021`
adds one `atomic_inc()` *before* the finish and jumps into the same unconditional
`kref_put()` tail. What `0021` changed is **reachability** — before it, this fault
case double-released the reset rwsem and the runtime-PM references, the encode
wedged, and the worker never ran on far enough to be caught here. So `0021` is
neither reverted nor amended: it fixed a confirmed lock-imbalance defect, and the
memory-safety defect it made observable was never its own. The generalisable lesson
is that **fixing the bug that aborts a path is how you find the bugs further down
it** — expect the next fault-injection run after any fix on an error path to
surface something new, and budget for it rather than reading it as regression.

Three of them (`0010`–`0012`) are **unmerged lore postings**, a provenance variant
distinct from `0007`'s merged-commit backport: they have no commit id, none is
claimed, and their retire trigger needs the posting to merge *and* the base to
absorb it. See [`backports/README.md`](../backports/README.md).

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
| `0010` naneng-combphy RTERM erratum | `backports/` lane — **unmerged lore posting**, `PATCHv1` by Shawn Lin (Rockchip), <https://lore.kernel.org/r/1774423383-36599-1-git-send-email-shawn.lin@rock-chips.com>. Imported by `scripts/import-lore-series.py` from the canonical thread archive; canonical mail kept at `backports/lore/U3/01.mbox`. **No commit id exists and none is claimed** | `sent-v1` — `Signed-off-by` author only. Vinod Koul asked for a `Fixes:` tag and an erratum reference on 2026-05-10; unanswered, no reroll. The question is about the commit message, not the register write | Posting merges **and** the pinned base absorbs it. Both — a merge alone leaves `v7.1.7` still missing it | 2026-08-10 | Matrix alias **U3**. Sets `FORCE_RTERM_DET_RDY` in `PHYREG26` for the SoCs whose cfg opts in, RK3588 included, so a PCIe peer's RX termination is detected at critical temperatures. Zero prerequisites; applies with no fuzz base-only and stacked; no other member touches `drivers/phy/`. Read [§ matrix U3](#u3) |
| `0011` dw-hdmi-qp N/CTS helper | `backports/` lane — **unmerged lore posting**, standalone `PATCHv3` by Simon Wright with **no cover letter and zero siblings**, <https://lore.kernel.org/r/86fcf349-0a7a-4618-9001-612371b0f71b@symple.nz>. Canonical mail at `backports/lore/U5/01.mbox`. **No commit id exists and none is claimed** | `sent-v3` — `Reviewed-by` **and** `Tested-by` Cristian Ciocaltea (Collabora), 2026-06-03, with no change requested | Posting merges **and** the pinned base absorbs it | 2026-08-10 | Matrix alias **U5**. Deletes dw-hdmi-qp's private N/CTS table, which disagrees with the shared helper at several TMDS rates, and calls `drm_hdmi_acr_get_n_cts()` — already exported by the base. Shares `dw-hdmi-qp.c` with `0012` without colliding. Read [§ matrix U5](#u5) |
| `0012` dw-hdmi-qp audio `-EOPNOTSUPP` | `backports/` lane — **unmerged lore posting**, `PATCHv1` by Detlev Casanova (Collabora), <https://lore.kernel.org/r/20260519-fix-hdmi-audio-warnings-v1-1-9608966c993f@collabora.com>. Canonical mail at `backports/lore/U6/01.mbox`. **No commit id exists and none is claimed** | `sent-v1` — two independent `Tested-by` (Maud Spierings 2026-07-06 on Orange Pi 5+, Diederik de Haas 2026-08-08). Sebastian Reichel asked only for a `Fixes:` tag; the payload was not contested | Posting merges **and** the pinned base absorbs it | 2026-08-10 | Matrix alias **U6**. With no mode set the audio hooks returned `-ENODEV`, which ASoC logs as a fault — reporters counted hundreds of `ASoC error (-19) … on i2s-hifi` lines on an idle board. Beyond log hygiene this protects the dmesg buffer that `0005`/`0006` are diagnosed from. Read [§ matrix U6](#u6) |
| `0013` rkvenc gated fault injection — **TEST INSTRUMENTATION, absent from production** | `ceralive/` lane — **first-party CeraLive**. Never submitted (no `Signed-off-by`, deliberately — see [`PROVENANCE.md` §8](PROVENANCE.md#8-first-party-patches-ceralive)). It instruments the imported `0001` driver, so its upstream position is the `0001` row's. Upstream Linux counterpart: **N/A** | `first-party-no-upstream` — this is QA scaffolding for a downstream driver; there is nothing upstream to be superseded by | Retire when `0001` retires wholesale, **or** when the negative paths `0014`–`0017` fix are covered by upstream tests that reach the same code. **Do not retire it merely because the drills passed once** — it is what makes a regression detectable | 2026-08-10 | Three Kconfig symbols (`VIDEO_ROCKCHIP_RKVENC_CERALIVE_TEST`, `VIDEO_ROCKCHIP_HDMIRX_CERALIVE_TEST`, `DMABUF_HEAPS_CERALIVE_TEST`) and six one-shot debugfs controls under `/sys/kernel/debug/rkvenc-test/`, each with a read-only `*_consumed` counter so a harness can tell a fault that fired from a knob the driver ignored. **Production absence is checked, not asserted**: a production-config build produces no `rkvenc_test.o` and no `rkvenc-test` string in `rkvenc.ko`, and all three symbols are on the image pipeline's `forbidden-symbols.list`, which the shipped `edge` config is gated against |
| `0014` rkvenc teardown and unwind — **`UNVALIDATED` on both boards** | `ceralive/` lane — **first-party CeraLive**. Never submitted. Fixes lifetime defects in `0001`, so its upstream position is the `0001` row's. Upstream Linux counterpart: **N/A** | `first-party-no-upstream` — upstream rkvenc is `WIP` (the same Collabora tracker as `0001`); there is no upstream VEPU580 driver whose teardown could be backported | Only if `0001` retires wholesale. Read [§ `0001`](#0001--do-not-retire-on-rkvenc-landing), which applies verbatim | 2026-08-10 | Six defects, all in the code that runs when something goes away: a session freed on the release drain's **timeout** path while the worker still dereferences `task->session`; that drain sleeping under `pending_lock`, which the completion path needs; a failed shared-IOMMU attach returning with the core already on `ccu->core_list` that devm then frees; `remove()` never clearing `queue->cores[]` or `srv->sub_devices[]`; a devm-allocated service torn down under open file descriptors; and a devm IRQ live across the whole of `remove()`. **The service-under-open-descriptors claim was OVERSTATED and is corrected by `0025`**: the drain it added is honoured only when it COMPLETES. On the timeout path its result was discarded, and on a service-node unbind it never ran at all, because the cores unbind first and `rkvenc_service_quiesce()` returned on `RKVENC_DRAIN_NOT_OWNER`. `srv` stayed `devm`-allocated either way, which a real Rock 5B+ KASAN `slab-use-after-free` in `rkvenc_dev_release()` proved. `0025` reference counts it. Fixed with `device_link_add()` to the service and CCU suppliers, a `LIVE → QUIESCING → DEAD` service state guarded by the **existing** session lock, a kref'd session, and one probe-stage ledger walked in exact reverse by both the probe error path and `remove()`. Harness: `tests/rkvenc-unbind.sh`, including a deliberate no-close fixture that must FAIL |
| `0015` rkvenc resource errors — **`UNVALIDATED` on both boards** | `ceralive/` lane — **first-party CeraLive**. Never submitted. Fixes error handling in `0001`, so its upstream position is the `0001` row's. Upstream Linux counterpart: **N/A** | `first-party-no-upstream` — same reason as `0014` | Only if `0001` retires wholesale | 2026-08-10 | Required-vs-optional classified from the binding `0001` itself ships: every `rkvenc-core` node declares three clocks, three resets and `iommus`, and neither declares `rockchip,sram`. `devm_clk_get()` failures were logged and returned 0 — turning a `-EPROBE_DEFER` from a not-yet-probed CRU into a permanently bound device with no clock; a failed `rkvenc_iommu_probe()` left `iommu_info` NULL and probe continued; reset acquisition turned every error into "no reset", removing the only recovery from a hung core. `clk_prepare_enable()`, `pm_runtime_get_sync()`, `rkvenc_hw_finish()` and `rkvenc_hw_reset()` returns were all discarded. Optional SRAM behaviour is preserved with one explicit log line. Harness: `tests/rkvenc-fault-qa.sh --case fail-clock-enable` |
| `0016` rkvenc ioctl bounds — **`UNVALIDATED` on both boards** | `ceralive/` lane — **first-party CeraLive**. Never submitted. Fixes the UAPI parser `0001` ships, so its upstream position is the `0001` row's. Upstream Linux counterpart: **N/A** | `first-party-no-upstream` — same reason as `0014` | Only if `0001` retires wholesale | 2026-08-10 | **The most serious defect in this wave.** `rkvenc_result()` located a read request's register class by its START offset only and then `copy_to_user()`'d the caller's own claimed size, so a request beginning one dword inside a class and claiming a large size read past the end of a kmalloc'd buffer into whatever followed it on the kernel heap and handed it to userspace — an information disclosure reachable by anything that can open `/dev/mpp_service`. Also: `offset + size` wrap, `size < 4` underflow and unaligned offsets in the parser; an element-vs-byte bound mismatch in `INIT_TRANS_TABLE` (one-byte overrun); three discarded error returns; and every allocation failure collapsed to `-ENOMEM`, which is now an `ERR_PTR` carrying the real errno. **Userspace-visible change**: a caller matching on `ENOMEM` will now see `EINVAL` or `EFAULT`. Harness: `tests/rkvenc-invalid-ioctl.c` with `tests/expected-errno.tsv` owning the expectations as reviewed data |
| `0017` HDMI-RX audio lifecycle — **`UNVALIDATED` on both boards** | `ceralive/` lane — **first-party CeraLive**. Never submitted. Fixes the audio path `0005` adds, so its upstream position is the `0005` row's — including that row's competing-upstream-series caveat | `first-party-no-upstream` — the upstream `PATCHv4` counterpart to `0005` does not carry this audio worker at all, so there is nothing upstream for this to be a version of | Retire together with `0005` if that row's four-part condition is ever met, since this patch fixes code `0005` introduces and would go with it | 2026-08-10 | The lock order is now written down on `struct snps_hdmirx_dev`, enumerated from `v7.1.7`'s own `sound/soc/codecs/hdmi-codec.c`: hdmi-codec invokes `->hook_plugged_cb()` under the ASoC card mutex and the installed callback reports a jack, so any path holding `work_lock` that calls into the codec closes a cycle against a path waiting for the audio worker under that lock — the same shape that already deadlocked the CeraLive **vendor** series, and one that fires only when audio is present. The old `cancel_delayed_work()` in `hdmirx_plugout()` was not merely weak but **ineffective**: it does not wait for a running worker, and the worker unconditionally rescheduled itself, so the work came back after every plugout. `clk_set_rate()` returns were discarded. 768000 is removed from `supported_fs` — CEA-861 tops out at 192 kHz and its only reachable effect was letting a garbage ACR-derived frequency pass `is_validfs()`. Harness: `tests/hdmirx-audio-fault-qa.sh` |
| `0018` truthful dma-heap partial registration — **KUnit VALIDATED, boot path `UNVALIDATED`** | `ceralive/` lane — **first-party CeraLive**. Never submitted. It restructures the registration `0009` extends, so its upstream position is the `0009` row's | `first-party-no-upstream` — mainline has no removal API to align with and no counterpart restructuring | Retire when the pinned base gains a real dma-heap removal API: at that point the sequence should UNWIND on failure and the KUnit case should assert the unwind rather than the retention. Also retires with `0009` | 2026-08-10 | `dma_heap_add()` has **no counterpart at this base** — no removal, no unregister, no atomic multi-add — so a failing second registration leaves the first heap live for the boot. This patch states that instead of hiding it: the error message names the partial state, and the retire condition is written beside the function. **No atomicity is claimed anywhere.** The sequence moves behind an injected `add_fn` so the failure is reachable from a test at all; the built-in `ceralive_system_heap_test` drives a fake failing add and asserts first-add retained / error returned unchanged / nothing further attempted, plus a non-vacuity case proving the injection is actually used. **All four cases PASS under `qemu-system-aarch64`** on the applied series. Nothing real is registered by the suite; `tests/check-kunit-heap.sh` re-asserts the boot's actual heaps from userspace, with an ANCHORED TAP match because `not ok 1 - <suite>` contains `ok 1 - <suite>` |
| `0019` rkvenc worker lock context + dma-buf API — **root-caused on REAL hardware, fix `UNVALIDATED`** | `ceralive/` lane — **first-party CeraLive**. Never submitted. Fixes two defects in the driver `0001` imports, so its upstream position is the `0001` row's. Upstream Linux counterpart: **N/A** | `first-party-no-upstream` — same structural reason as `0014`: there is no upstream VEPU580 driver whose locking could be fixed instead | Only if `0001` retires wholesale. If upstream rkvenc ever lands, re-check both defects against it before assuming they are gone — the dma-buf half is an API-era mistake any downstream port of this driver will share | 2026-08-10 | **Found by a REAL Rock 5B+ KASAN+LOCKDEP boot during a plain 1080p encode — no fault injection, no unbind.** Two INDEPENDENT defects, both `0001`'s as imported. (1) `rkvenc_task_worker_default()` holds `queue->running_lock` via `spin_lock_irqsave()` and, still holding it with interrupts off, takes `queue->pending_lock` — which `0001` declares a `struct mutex`. That is `BUG: sleeping function called from invalid context at kernel/locking/mutex.c:623` plus lockdep's `[ BUG: Invalid wait context ]` for `{3:3}` outside `{4:4}`, and untreated it can schedule with interrupts disabled. `pending_lock` becomes a `spinlock_t` at all three of its sites; `running_lock` stays held across the dequeue **on purpose**, because claiming an idle core and taking the task that will occupy it must be one step or two workers can claim the same `core_id`. Neither `pending_lock` section sleeps or is more than an O(1) list operation. (2) `rkvenc_dma_import_fd()` and `rkvenc_dma_release_buffer()` call the LOCKED dma-buf entry points, which since the dynamic-importer split assert the caller holds `dmabuf->resv` — `v7.1.7` `drivers/dma-buf/dma-buf.c:1179` is `dma_resv_assert_held(attach->dmabuf->resv)`. rkvenc attaches with plain `dma_buf_attach()` and registers no `dma_buf_attach_ops`, so it is a static importer and every import WARNed; the calls move to `dma_buf_map_attachment_unlocked()` / `dma_buf_unmap_attachment_unlocked()`. **The two are unrelated** — the dma-buf WARNING fires in ioctl context on a task that never touches either queue lock; the captured log only made them look coupled because console output from the two CPUs interleaved. **No lockdep suppression of any kind.** Runtime re-test on the debug slot is the confirming evidence and is pending |

| `0020` rkvenc service survives a single core's unbind — **root-caused on REAL hardware, fix `UNVALIDATED`** | `ceralive/` lane — **first-party CeraLive**. Never submitted. It fixes `0014`'s own service lifetime model, not imported code, so unlike `0019` its upstream position is `0014`'s row and not `0001`'s. Upstream Linux counterpart: **N/A** | `first-party-no-upstream` — the LIVE/QUIESCING/DEAD model this corrects is `0014`'s invention; mainline has no rkvenc service to have gotten it right or wrong | Retire together with `0014`. It is not separable: with `0014` gone there is no service state machine left to keep reversible | 2026-08-10 | **Found by REAL Rock 5B+ fault injection: two bind-fault cases unbound core 0, re-bound it cleanly, watched the kernel print its own `rkvenc core 0 probe success` — and then could not `open("/dev/mpp_service")` at all, for the rest of the boot.** `0014`'s `rkvenc_core_unwind()` ended its first step with `rkvenc_service_quiesce(srv)`, which drives `srv->state` `LIVE -> QUIESCING -> DEAD`; `srv->state` is assigned in exactly three places in the whole driver — `LIVE` once in `rkvenc_service_probe()`, then `QUIESCING` and `DEAD` inside the quiesce — so **nothing restores `LIVE`**, and `rkvenc_dev_open()`'s `state != RKVENC_SRV_LIVE` half kept refusing after the sub-device came back. A single core's bind/unbind is transient; the state it drove is terminal. The drain body is factored out as `rkvenc_service_drain()` and the terminal state becomes the caller's: `rkvenc_service_quiesce()` still ends `DEAD` for `rkvenc_service_remove()` and `rkvenc_shutdown()`, while the unwind calls the new `rkvenc_service_quiesce_for_core()`, which returns a **fully drained** service to `LIVE`. **The quiesce is NOT removed** — a bare removal would drop the abort-and-drain that lets an in-flight waiter reach `release()` before the core frees its IRQ, which is exactly what `0014` added and what `tests/rkvenc-unbind.sh`'s inflight and held-open-FD cases prove. **The refusal is NOT weakened**: while the core is absent `!sub_devices[MPP_DEVICE_RKVENC]` still fails every open with `-ENODEV`, and that guard — unlike `state` — is reversible, because the core's next successful probe repopulates it. A drain that TIMES OUT still ends `DEAD`, since sessions that outlived it still point at the departing core. No test expectation changes: `tests/rkvenc-fault-qa.sh` already asserted the correct behaviour with its post-re-bind `qa_encode`, and `tests/rkvenc-unbind.sh` unbinds the SERVICE node, which is why it never caught this. **The parenthetical this row originally carried — that the service node's own `remove()` "quiesces permanently and correctly" — was WRONG and is corrected by `0025`**: the `NOT_OWNER` early return introduced here is precisely what made a service-node `remove()` skip its wait entirely, since the cores unbind first and take the `LIVE -> QUIESCING` transition before the service ever reaches it |

| `0021` rkvenc balanced hw_run teardown — **root-caused on REAL hardware, fix `UNVALIDATED`** | `ceralive/` lane — **first-party CeraLive**. Never submitted. The unconditional release it fixes is `0001`'s as imported, so like `0019` its upstream position is the `0001` row's; `0015` only made the failing acquire reachable. Upstream Linux counterpart: **N/A** | `first-party-no-upstream` — same structural reason as `0014`: there is no upstream VEPU580 driver whose task lifecycle could be fixed instead | Only if `0001` retires wholesale. If upstream rkvenc ever lands, re-check the asymmetry against it rather than assuming it is gone — an acquire in one function released by another is a shape any downstream port of this driver can inherit | 2026-08-11 | **Found by REAL Rock 5B+ fault injection: `tests/rkvenc-fault-qa.sh --case fail-clock-enable` produced `WARNING: bad unlock balance detected!` from `rkvenc_task_finish+0x98`, `DEBUG_RWSEMS_WARN_ON(tmp < 0)` with the reset group's rwsem count at `0xffffffffffffff00`, and `Runtime PM usage count underflow!` — and those counts stay wrong for the rest of the boot, not just for that task.** `rkvenc_hw_run()` acquires two runtime-PM references, a wakeup source, three clocks and the reset group's read lock, and unwinds every one of them itself: five paths reach its error labels and two more return outright. `rkvenc_task_finish()` released the same set **unconditionally**, guarded only by `mpp->reset_group` being non-NULL — a static device-topology fact, true on every board that wires the resets, that says nothing about what *this* task did. A task `hw_run` refused still arrives there through the worker's own `run_ret` failure path, so **every** early exit double-released: an `up_read()` with no matching `down_read()`, `rkvenc_hw_clk_off()` on clocks that were never enabled, and PM references `hw_run` had already put. **This is a production path, not a test-only one** — the injected fault sits exactly where a genuine `clk_prepare_enable()` or PM-resume failure lands, which is why `0013` placed it there. The fix is one task-state bit, `TASK_STATE_HW_HELD`: set immediately after the last acquire and cleared at `err_pm`, the common tail of all three error labels, so it is true exactly when `hw_run` returned holding the set; `rkvenc_task_finish()` takes it with `test_and_clear_bit()`, which also makes the teardown single-shot so an IRQ and a timeout racing to finish one task release once. The bit is set **before** the timeout work is scheduled and before the start register is written, because either can hand the task to `rkvenc_task_finish()` on another CPU immediately. A refused task is additionally marked `abort_request` before it is woken, so a `POLL` waiter takes `rkvenc_wait_result()`'s `-ENODEV` arm instead of being handed zeroed status registers as a clean encode. **`0015`'s error paths are NOT changed** — they are correct in isolation, and the asymmetry was always on the release side. **`0014`'s quiesce/drain and `0020`'s per-core requiesce are untouched.** The IOMMU activate/deactivate pair is deliberately left alone: `hw_run` already owns both sides of it. No test expectation changes — `rkvenc-fault-qa.sh` already asserted the correct behaviour with its post-fault `qa_encode` |
| `0022` rkvenc ioctl request coverage and element bounds — **root-caused on REAL hardware; its first version BROKE production encode on REAL hardware and was amended in place; amendment `UNVALIDATED`** | `ceralive/` lane — **first-party CeraLive**. Never submitted. It completes `0016`, which is itself a fix to the UAPI parser `0001` imports, so its upstream position is the `0001` row's. Upstream Linux counterpart: **N/A** | `first-party-no-upstream` — same structural reason as `0014` | Retire together with `0016`, i.e. only if `0001` retires wholesale. Read [§ `0001`](#0001--do-not-retire-on-rkvenc-landing) | 2026-08-11 | **Found by REAL Rock 5B+ `rkvenc-invalid-ioctl --all-malformed`, which failed 4 of 8 against `tests/expected-errno.tsv` — so `0016` did not finish the job, and being marked done proved nothing.** Three of the four were driver defects. (1) `class-overrun` was **accepted with `rc=0`**: a register request is SPLIT across every class it overlaps and each part clamped to that class's range, so bytes no class owns were silently discarded rather than refused — and the register map has real holes (class `BASE` ends at `0x0058`, class `PIC` starts at `0x0280`) and a hard end at `0x5354`. `0016` bounded the *copy* in `rkvenc_result()`, which is the right fix for the heap over-read, but that runs at `POLL` time and nothing rejected the request at submit time. (2) `trans-table-odd-size` was accepted because `0016` bounded `INIT_TRANS_TABLE` by **bytes** but not by **alignment**: `2*N+1` still divides to `N` whole entries, so an odd size well inside `sizeof(trans_table)` passed and left one `u16` half written while `trans_count` claimed it whole. (3) `bad-user-pointer` returned `-EIO` because the register-write `copy_from_user()` still did — an I/O-error claim about the hardware for what is an unreadable *user address*; `0016` fixed the `copy_to_user()` twin and missed this one. Reading the same paths for the cause turned up **two more of the same shape that no drill case covers**: `w_req_cnt`/`r_req_cnt` accumulate across every message in one ioctl and were unbounded, so two write messages each spanning all nine classes wrote 18 parts into a 9-element array inside the `kzalloc`'d task; and `rkvenc_extract_reg_offset_info()` bounded ELEMENTS while copying BYTES — the identical mismatch `0016` fixed in `INIT_TRANS_TABLE` — so `8*128 + 7` bytes passed the count check and overran `elem[]` by seven, partial trailing element included. **The first version of this patch then broke every hardware encode, and the shipped one is the amendment.** It required the summed clamped parts to EQUAL the request's size, on the stated premise that a request lying wholly inside the classes it names is what `librockchip-mpp` sends. A cold-boot control encode on a real Rock 5B+ — nothing armed, no fault injected — proved that premise **false**: MPP's class-`BASE` write is `offset 0 size 96`, `reg_msg[]` owns `[0x0000,0x005c)` = 92 bytes, so the request's last dword lands in the 137-dword hole between `BASE` and `PIC`, and every production task was refused (`write request 00000000+96 names 4 bytes no register class owns`, `alloc task failed: -22`) for **0 bytes out**, against **1,854,524 bytes** from the same board one RAUC slot earlier on the 19-patch kernel. `reg_msg[]` is a **sparse** map — no two of its nine classes abut, the holes run from six dwords (`SQI`→`SCL`) to 770 (`PIC`→`RC`) — so the clamp has dropped edge dwords silently since `0001` imported it, and an equality test cannot tell that harmless pre-existing drop apart from a real malformation. `req_coverage_check()` therefore asks **where** the dropped bytes went, not how many: the clamped parts are disjoint subranges, so they sum to the span they cover only when that span has no hole inside it, and requiring `sum == span` is exactly "the split consumed ONE contiguous run". A request spilling off a class's edge into the neighbouring hole (MPP's 96-byte write) is one run and is accepted and clamped as before `0022`; a request stitched from several runs with the map's holes *between* them (`class-overrun`) is still `-EINVAL`. Contiguity alone cannot catch a request running past the LAST class, since no following class is there to notice, so the request is additionally bounded by the map's own extent — computed from `reg_msg[]`, not hardcoded. **The per-class split, the clamp, and all of `0016`'s shape and window checks are unchanged**, and the amendment does **not** tighten what the clamp always tolerated: a request may still spill into an adjacent hole by as much as that hole holds, and those bytes are still dropped silently. Memory safety on this path is `0016`'s window check; this check refuses a misleading *shape*. The inclusive/half-open mismatch between `req_over_class()` and `rkvenc_result()`'s class lookup, and `reg_msg[]`'s `BASE` end being one dword short of what MPP writes, are **pre-existing and deliberately not touched** — neither is changeable without a board. **`valid-after-failures` still fails and this patch does not fix it** — read [§ `0022`](#0022--what-it-fixes-what-it-does-not-and-the-one-case-still-red). No test expectation changes: `expected-errno.tsv` already demanded these values |
| `0023` rkvenc worker task lifetime — **root-caused on REAL hardware, fix `UNVALIDATED`** | `ceralive/` lane — **first-party CeraLive**. Never submitted. Both dereferences it removes are `0001`'s as imported, so like `0019` and `0021` its upstream position is the `0001` row's. Upstream Linux counterpart: **N/A** | `first-party-no-upstream` — same structural reason as `0014`: there is no upstream VEPU580 driver whose task lifetime could be fixed instead | Only if `0001` retires wholesale. If upstream rkvenc ever lands, re-check the worker against it rather than assuming it is gone — "finish the task, then read it again" is a shape any downstream port of this driver can inherit | 2026-08-11 | **Found by REAL Rock 5B+ fault injection on the run that CONFIRMED `0021`: `tests/rkvenc-fault-qa.sh --case fail-clock-enable` on a KASAN+`PROVE_LOCKING` kernel produced `BUG: KASAN: use-after-free in rkvenc_task_worker_default+0xcfc/0x10dc`, `Read of size 8 at addr ffff00010da88030`, shadow `ff` across the line and page `refcount:0` — long freed, not freshly poisoned.** `rkvenc_task_finish()` ends in `kref_put(&task->ref, rkvenc_free_task_callback)`, which `kfree()`s the whole `struct rkvenc_task`. A task carries exactly **two** references — the allocator's from `rkvenc_alloc_task()` and the one `rkvenc_dev_ioctl()` takes for the waiter — and **three** places drop one: the worker (inside `rkvenc_task_finish()`), `rkvenc_wait_result()`, and the release drain in `rkvenc_dev_release()`. Whichever puts last frees, and the worker's put is last whenever the waiter got there first — which the release drain does with nothing between its `wait_event_timeout()` on `TASK_STATE_DONE` and its `kref_put()`, while the worker still has `running_lock` and a `list_del_init()` to go. The worker then kept using the pointer in **two** places, both `0001`'s as imported: its IRQ arm calls `rkvenc_task_finish()` and the timeout arm immediately below re-reads `mpp_task->state`; its `hw_run`-failure arm calls `rkvenc_task_finish()` and then `wake_up(&pending_task->wait)`. **The report names the first of the two, to the byte.** `pahole` on a KASAN+`PROVE_LOCKING` `arm64` build of this exact applied series puts `rkvenc_mpp_task.state` at **offset 48 (`0x30`), size 8** — behind three `list_head`s — and `sizeof(struct rkvenc_task)` at **11408 bytes**, which is over `KMALLOC_MAX_CACHE_SIZE`, so `kzalloc()` serves it from the **page allocator**, page-aligned: exactly why KASAN named a *page* with `refcount:0` instead of a slab object. `0xffff00010da88030` is `0x30` into a 16 KiB-aligned allocation, and `test_bit()` on an `unsigned long` is an 8-byte instrumented **read** — `set_bit()` would have printed a write and `atomic_inc(&abort_request)` a 4-byte read-write at offset 192. `wait` is at offset **112**, so the failure arm's `wake_up()` is a *different* address and was not the one reported; it is fixed all the same. **The fix is that the worker stops touching a task it has handed over.** The IRQ arm nulls its local afterwards, which costs nothing reachable: `rkvenc_hw_irq()` and `rkvenc_task_timeout_work()` both claim a task with `test_and_set_bit(TASK_STATE_HANDLE, ...)`, and the timeout side does it with the encoder's IRQ disabled, so `TASK_STATE_IRQ` and `TASK_STATE_TIMEOUT` are **never both set** on one task — the second arm's test could only ever be false on live memory, and had that gate broken, the old code would have called `rkvenc_task_finish()` twice on one task and put one reference twice. The failure arm loses its trailing `wake_up()`, which was redundant as well as unsafe: `rkvenc_task_finish()` sets `TASK_STATE_DONE` and wakes `task->wait` on **every** path, including `0021`'s teardown-skipping one. **`0021` is neither reverted nor amended.** It is not the cause: it adds one `atomic_inc()` *before* the failure arm's finish and jumps into the same unconditional `kref_put()` tail, and it does not touch the IRQ/timeout arms at all. What it changed is **reachability** — before it, this fault case double-released the reset rwsem and the runtime-PM references, the encode wedged, and the worker never ran on far enough to be caught here. Reverting it would reinstate a confirmed lock-imbalance defect to hide a memory-safety one. **The reference-counting model is unchanged**: two references, two owners, three drop sites, exactly as `0001` and `0014` left them, and no `kref_get()` is added to hold the window open instead of closing it. `rkvenc_task_finish()` itself, `0014`'s quiesce/drain and `0020`'s per-core requiesce are untouched. **This fix is HOST-VERIFIED ONLY** — `W=1` build-clean under gcc 16.1, every repo gate green, and NO hardware re-run. No test expectation changes: the fault-QA harness already asserts the correct behaviour |
| `0024` rkvenc secondary-core IOMMU domain lifetime — **root-caused AND re-verified on REAL hardware** | `ceralive/` lane — **first-party CeraLive**. Never submitted. The NULL-domain window is `0020`'s as written and the unguarded attach is `0001`'s as imported, so like `0019`, `0021` and `0023` its upstream position is the `0001` row's. Upstream Linux counterpart: **N/A** | `first-party-no-upstream` — same structural reason as `0014` and `0023`: there is no upstream VEPU580 driver whose multi-core IOMMU sharing could be fixed instead | Only if `0001` retires wholesale. If upstream rkvenc ever lands, re-check how it shares a domain between the CCU's cores rather than assuming this is gone — "a secondary borrows the main core's page tables" is a shape any downstream port of this driver can inherit | 2026-08-11 | **Found by a REAL Rock 5B+ kernel Oops on a KASAN+`PROVE_LOCKING` boot: `KASAN: null-ptr-deref in range [0x0000000000000020-0x0000000000000027]`, `Internal error: Oops: 0000000096000005`, `pc : __iommu_attach_group+0x15c/0x278`, `x20 = 0`, `x22 = 0`, `x0 = 0x20`, reached from `rkvenc_iommu_attach+0x98` ← `rkvenc_hw_run+0x22c` ← `rkvenc_task_worker_default+0x828`.** The faulting load is pinned to a struct member rather than guessed: in the pinned `v7.1.7` tree `struct iommu_domain` lays out `type` at `0x00`, `cookie_type` at `0x04`, `is_iommupt` at `0x08`, `ops` at `0x10` and `dirty_ops` at `0x18`, so **`owner` is at `0x20`** — and `__iommu_attach_group()` reads exactly that, through `domain_iommu_ops_compatible()`, before doing anything else. It is `domain->owner` with `domain == NULL`. **How the domain became NULL.** RK3588 wires two encoder cores behind one CCU and the secondary borrows the main core's IOMMU domain at probe (`rkvenc_attach_ccu()`'s `else` arm). When the **main** core unbinds, `rkvenc_core_unwind()` detaches every secondary and NULLs its domain — correctly; the page tables are going away. When the main core comes **back** it re-probes into the `!ccu->main_core` arm, which only claims the main slot: the arm that shares a domain is the `else`, and only a probing **secondary** reaches it. The secondary never re-probes, so its domain stays NULL for the rest of the boot — while it is **still in `queue->cores[]` with its idle bit set**, because the unwind's queue step clears the slot of the core that is *unbinding* and that is not this one. The board log shows exactly this: three `attach ccu as core 0 [main]` lines after the unbind cycles and **not one** `attach ccu as core 1`. The next task the worker sent to the second core Oopsed, the driver wedged, and the following reboot took **745 s** against ~130-150 s healthy. **The fix makes dispatchability and domain-validity the same fact**: the unwind unpublishes a secondary at the moment it takes its domain away, a core that becomes main re-shares its domain with the secondaries already on `ccu->core_list` and republishes each one that takes it, and `rkvenc_iommu_attach()` refuses a NULL domain or group outright instead of handing it to `iommu_attach_group()`. That last guard matters on its own: the pre-existing `info->domain == iommu_get_domain_for_dev(info->dev)` comparison **cannot** catch the case, because `iommu_get_domain_for_dev()` returns the core's DEFAULT domain, which is never NULL, so `NULL != default` and the call went ahead. With it, `rkvenc_hw_run()` unwinds through `0021`'s balanced `err_unlock` and the task fails as `-ENODEV` instead of taking the machine down. Publication and unpublication become **one idempotent pair of helpers** keyed on the stage bit they already owned, so the four call sites cannot drift. **Cold boot is unchanged**: the first core to probe finds an empty `ccu->core_list`, so the re-share is a no-op and initial bring-up runs the code it always did. **This does NOT fix the `possible recursive locking` warning on `&rg->rw_sem`** that accompanies the Oops — that is a separate, tracked defect: `rkvenc_hw_run()` returns holding `down_read()` and the single `rkvenc-worker` kthread necessarily nests it when it dispatches to the second core, because `find_first_bit()` only picks core 1 while core 0 is busy. It is reported once per boot because lockdep disables itself afterwards, and it cannot deadlock today because nothing in the driver takes that rwsem for write. **RE-VERIFIED ON HARDWARE**: `W=1` build-clean under gcc 16.1, every repo gate green, and the unbind/rebind-then-encode sequence that produced the Oops re-run repeatedly on a KASAN+lockdep boot with zero KASAN, zero Oops and zero recursive-locking reports, both cores confirmed dispatchable afterwards. No test expectation changes |
| `0025` rkvenc service-node teardown lifetime — **root-caused AND re-verified on REAL hardware** | `ceralive/` lane — **first-party CeraLive**. Never submitted. The devm-allocated service torn down under open descriptors is `0014`'s own, the `NOT_OWNER` early return is `0020`'s, and the mutex inside the wait condition is `0014`'s — so unlike `0019`/`0021`/`0023` its upstream position is `0014`'s row, not `0001`'s. Upstream Linux counterpart: **N/A** | `first-party-no-upstream` — the service object, its state machine and its drain are all `0014`'s invention; mainline has no rkvenc service whose teardown could be backported instead | Retire together with `0014` and `0020`. It is not separable: with `0014` gone there is no service object to reference count and no drain to make wait | 2026-08-11 | **Found on a REAL Rock 5B+ KASAN+`PROVE_LOCKING` boot by the harness's own deliberate no-close fixture, `tests/rkvenc-unbind.sh --states timeout-negative`: `FAIL unbind COMPLETED with a file descriptor still open`, followed at close time by `BUG: KASAN: slab-use-after-free in __mutex_lock+0x1128/0x1158` from `rkvenc_dev_release+0x100/0x740`.** The freed object is `srv`: `devm_kzalloc()`'d on the service platform device, so `devres_release_all()` frees it the instant `rkvenc_service_remove()` returns, and `rkvenc_dev_release()` then takes `mutex_lock(&srv->session_lock)` on it. **Why the wait that was supposed to prevent this never happened.** `RKVENC_QUIESCE_TIMEOUT_MS`'s own comment states teardown "does NOT proceed to release state those descriptors can still reach", and `rkvenc_service_remove()` broke it two ways. On a **SERVICE-node** unbind the CORES unbind first — `__device_release_driver()` runs `device_links_unbind_consumers()` (`dd.c`) before `device_remove()` — so the first core's `rkvenc_service_quiesce_for_core()` owns the `LIVE -> QUIESCING` transition, and the service's own `rkvenc_service_quiesce()` receives `RKVENC_DRAIN_NOT_OWNER` and **returns without waiting even once**. That is the NORMAL path for the node this harness unbinds, not an edge case. And when it did own the transition, `RKVENC_DRAIN_TIMED_OUT` was discarded — the board printed `quiesce timed out with 1 session(s) still open; refusing to release service state` and then released it anyway, so the message was untrue. **A third defect in the same drain**, predicted from source and then observed: `rkvenc_service_sessions_gone()` took `session_lock`, and every caller is a `wait_event*()` condition, which `___wait_event()` evaluates AFTER `prepare_to_wait_event()` has set the task state — `WARNING: kernel/sched/core.c:9091 at __might_sleep+0x108/0x154` from `rkvenc_service_drain+0x260/0x3f0`. It had never fired in any prior QA because no run had reached the wait loop with a session still open; it is now a lockless `READ_ONCE()`. **The fix is a lifetime change, not a wait change, because neither naive wait works.** An UNINTERRUPTIBLE wait parks the sysfs `unbind` writer in `D` state where no signal reaches it, while the process tree that would close the descriptor is typically the one blocked on that writer — a genuine deadlock, and a wedged rkvenc task turns `systemctl reboot` into an ~8-minute affair. An INTERRUPTIBLE wait alone still returns into a `void`-ish `remove()` that frees `srv` with the descriptor open. So `srv` stops being `devm`-allocated and becomes **reference counted**, anchored on a `struct device` it now EMBEDS and publishes with `cdev_device_add()`, whose `->release()` frees it: the driver binding holds one reference and every open file holds another. The kobject parenting `cdev_device_add()` establishes is what covers `__fput()`'s `cdev_put()` — which runs AFTER `->release()` returns and which no explicit put of the driver's could reach. `remove()` then quiesces and waits **unbounded and interruptible**; the 10 s bound stays where it belongs, on the TRANSIENT per-core drain, which has somewhere to recover to. **Reference counting `srv` alone would only move the use-after-free to the core**: `struct rkvenc_dev` is `devm`-allocated on the CORE's device, and a surviving session reaches it through `session->mpp`/`task->mpp` — `rkvenc_free_task_callback()` decrements `mpp->task_count`, `rkvenc_task_finalize()` takes `mpp->iommu_info`'s rwsem, and `rkvenc_task_timeout_work()` calls `disable_irq(mpp->irq)` up to two seconds after a task that was running when the core went away. A core's unwind therefore **severs** those pointers at the one point where its IRQ is already silent and the worker already drained, and every consumer treats the NULL as nothing left to release — the same explicit, checkable fact `0020` made of `sub_devices[]` and `0024` of `iommu_info->domain`. The DMA session additionally takes a reference on the device it attached to, because its dma-buf detach outlives that core. **NOT a task-lifetime change**: no `kref_get()` is added and `0021`/`0023`'s two-reference model is untouched. **Known and deliberately NOT fixed here**: a task abandoned on `queue->pending_list` by an abort keeps its allocator reference and is never freed — a leak on a teardown path, not a use-after-free, and closing it means changing the reference model `0023` just stabilised. **RE-VERIFIED ON HARDWARE, before/after on one board with only the module swapped**: the `timeout-negative` fixture goes FAIL → PASS, the log shows `teardown waiting for 1 open file descriptor(s)` then `teardown wait interrupted with 1 descriptor(s) still open; the service outlives this unbind on its reference count`, and KASAN, `__might_sleep`, `Oops`, `bad unlock balance` and recursive-locking counts are all **0**. All four states — `unbind-idle`, `unbind-held-fd`, `unbind-inflight`, `unbind-timeout-negative` — pass, 20 unbind/rebind cycles complete, and every encode returns the canonical **1,854,524 bytes**. The sever is exercised by a separate stress, because the harness cannot reach it: `qa_hold_fd()` only `open(2)`s the node, so its session never attaches to a core and never owns a task. No test expectation changes |
| `0026` hdmirx register lock hardirq context — **root-caused AND re-verified on REAL hardware** | `ceralive/` lane — **first-party CeraLive**. Never submitted. `rst_lock`, its four accessors and both hardirq handlers are all v7.1.7's own as imported, untouched by `0002`/`0003`/`0005`/`0006`/`0011`/`0012`/`0017`, so its upstream position is the `0002` row's — the first row that carries this driver. Upstream Linux counterpart: **N/A** | `first-party-no-upstream` — mainline carries the defect; no counterpart fix has been posted for `snps_hdmirx`'s register lock | Retire when mainline `snps_hdmirx` classifies `rst_lock` as raw itself, or when it stops entering the register accessors from hardirq. Do **not** retire with `0017`: that patch owns `audio_lock`/`work_lock` and never touches this one | 2026-08-12 | **Found on a REAL Rock 5B+ the first time a physical HDMI source was attached to a lockdep boot — which is why nine prior hardware attempts never saw it.** During probe, before a shell exists: `BUG: Invalid wait context`, `swapper/0/0 is trying to lock ffff0001011bd590 (&hdmirx_dev->rst_lock){-.-.}-{3:3} at hdmirx_readl+0x2c/0xa0`, `context-{2:2}`, from `hdmirx_cec_hardirq+0x8c/0x564` ← `__handle_irq_event_percpu`. `spinlock_t` is registered `LD_WAIT_CONFIG` — a sleeping `rt_mutex` under `PREEMPT_RT` — and hardirq context is `LD_WAIT_SPIN`, which may not wait on one. That is exactly the nesting `CONFIG_PROVE_RAW_LOCK_NESTING` exists to report, and it is a true report, not a false positive. **The report costs far more than the lock it names**: `print_lock_invalid_wait_context()` calls `debug_locks_off()`, which never re-arms for the rest of the boot, so every later `possible recursive locking`, `bad unlock balance` and lock-order inversion in **any** subsystem — including every rkvenc assertion `0021`/`0023`/`0024`/`0025` are validated against — goes silently unreported. Firing during probe meant no boot could have both live HDMI and live lockdep. **CEC is the first offender, not the only one.** The `hdmi` interrupt is requested with `devm_request_irq()` and **no threaded half at all**, and `hdmirx_hdmi_irq_handler()` opens with twelve `hdmirx_readl()` calls before dispatching to sub-handlers that add more reads and writes; `rk3588-extra.dtsi` declares that line `IRQ_TYPE_LEVEL_HIGH`, so its status **must** be read and acked in the primary handler or the line re-asserts forever. **Deferring only the CEC read to a thread would therefore have moved the report to `hdmirx_hdmi_irq_handler()`, not removed it** — which is why the fix is the lock's classification and not the handler's shape. **The fix is one lock, promoted**: `rst_lock` becomes `raw_spinlock_t` and its four acquire sites become `guard(raw_spinlock_irqsave)`. It is deliberately **not** split into a raw MMIO lock plus a sleeping reset lock — that would destroy the register-access-versus-DMA-reset exclusion the lock exists for, which is the whole reason it is called `rst_lock`. Scope, IRQ-save discipline and leaf position are unchanged, and on a non-`PREEMPT_RT` build the emitted code is identical; what changes is that lockdep is now told the truth about a lock the driver has always taken from hardirq. **Legal only because nothing under it sleeps, checked at every site rather than assumed**: three of the four accessors wrap `readl()`/`writel()` alone, and the fourth, `hdmirx_reset_dma()`, calls `reset_control_reset()` — which `drivers/reset/core.c` does not annotate `might_sleep()` anywhere, whose body is an SRCU read section (legal in hardirq) around `rcdev->ops->reset`, and which on this SoC returns `-ENOTSUPP` before reaching a provider at all, because `rk3588-extra.dtsi` points the hdmirx resets at `&cru` and `rockchip_softrst_ops` publishes only `.assert` and `.deassert`. **Known and deliberately NOT fixed here**: that same fact makes `hdmirx_reset_dma()` a no-op on RK3588 — a real upstream gap, unrelated to lock context, and not closeable without a reset provider this SoC does not have. `audio_lock` and `work_lock` are untouched and are not the next report: both are taken only from process and workqueue context. **RE-VERIFIED ON HARDWARE, on the boot the defect requires**: a `rock-edge-test` candidate carrying this patch, installed to the Rock 5B+'s A slot with the same physical 4K30 HDMI source still attached and locked (`v4l2-ctl --query-dv-timings` 3840x2160, 296712000 Hz). `/proc/interrupts` proves both hardirqs genuinely ran — `rk_hdmirx_cec` **1** and `rk_hdmirx-hdmi` **37**, the identical counts the failing boot produced — and `/proc/lockdep_stats` reads `debug_locks: 1` after boot completes AND again after the full QA workload, against `debug_locks: 0` before a shell even existed on the previous boot. Across the whole boot: `Invalid wait context` **0**, `possible recursive locking` **0**, `bad unlock balance` **0**, circular-locking **0**, `BUG:` **0**, `WARNING:` **0**, `KASAN` **0**, `Oops` **0**, `Call trace:` **0**, and zero mentions of `rst_lock` anywhere in the log. No regression in the paths this could plausibly have touched: the `hdmirx` ALSA card still registers with a live capture PCM (`03-00: fddf8000.i2s-i2s-hifi … capture 1`, listed by `arecord -l`), `/dev/cec0` still enumerates as the `snps_hdmirx` adapter with its full capability set, and rkvenc hardware encode returns the canonical **1,854,524** bytes on two consecutive runs. No test expectation changes |

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

### `0022` — what it fixes, what it does not, and the one case still red

**Read this part first: `0022` v1 fixed its three cases and broke every encode.**

The drill below is what `0022` was written for, and on a board it worked: after
`0022`, `class-overrun` → `EINVAL`, `trans-table-odd-size` → `EINVAL` and
`bad-user-pointer` → `EFAULT` all hold, 7 of 8, exactly as predicted. On the *same*
kernel, a **cold-boot control encode — first encode of a fresh boot, nothing armed,
no fault, no unbind** — produced 0 bytes and `SIGABRT`:

```
rkvenc_extract_task_msg:416: write request 00000000+96 names 4 bytes no register class owns
rkvenc_dev_ioctl:1302: alloc task failed: -22
```

An A/B on the same board one RAUC slot apart settled that it was the kernel and not
the rig: 21-patch slot 0 bytes, 19-patch slot **1,854,524 bytes**, byte-identical to
the known-good figure.

The arithmetic, recomputed against `reg_msg[]` itself. `base_e` is the **inclusive**
address of a class's last dword, so `RKVENC_CLASS_BASE = { 0x0000, 0x0058 }` owns
bytes `[0x0000, 0x005c)` — 92 of them. `librockchip-mpp` writes `offset 0, size 96`,
whose last dword sits at `0x005c`; `RKVENC_CLASS_PIC` does not start until `0x0280`.
That one dword belongs to **no class**, and `rkvenc_update_req()`'s clamp has dropped
it silently ever since `0001` imported the driver. It is not a defect — it is the
behaviour every working encode this project has ever recorded ran on. `0022` v1's
`req_fully_covered()` was an exact byte-count equality, so it read that pre-existing
harmless drop as a hard failure and refused the request.

This is **not** a `BASE`/`PIC` quirk. `reg_msg[]` is a sparse map and **no two of its
nine classes abut** — every neighbouring pair is separated by a hole, the narrowest
being six dwords (`SQI` → `SCL`) and the widest 770 (`PIC` → `RC`) — and the map
stops dead after `DBG`. Any request that runs off any class's edge lands in a hole.
An equality test was therefore always going to refuse real traffic; MPP's `BASE`
write is simply the shape that reaches it first.

**The amendment.** `req_coverage_check()` replaces "how many bytes were dropped"
with "**where** they went", which is the distinction that actually separates the two
populations:

- the split covered **one unbroken run** and the request merely spilled off its edge
  into the neighbouring hole — MPP's 96-byte write. Accepted and clamped, exactly as
  before `0022`.
- the split covered **several disjoint runs with the map's holes between them**, so
  the driver stitched pieces of the register file together and reported the whole
  span as programmed, or read back. That is `class-overrun`, and it is still
  `-EINVAL`.

The clamped parts are disjoint subranges of the request, so they sum to the span they
cover **only** when that span has no hole inside it; requiring `sum == span` *is*
"one contiguous run", and it needs no constant. Contiguity alone cannot catch a
request running past the last class — there is no following class to notice — so the
request is additionally required to lie inside the map's own extent, computed by
walking `reg_msg[]` rather than hardcoded, so a map with different holes or none
needs no change here.

What the amendment deliberately does **not** do: it does not tighten what the clamp
has always tolerated. A request may still spill into an adjacent hole by as much as
that hole holds, and those bytes are still dropped silently. That is the pre-`0022`
contract, memory safety on this path is `0016`'s window check, and this check's job
is to refuse a misleading *shape*. Widening `reg_msg[]`'s `BASE` end to the 24 dwords
MPP actually writes would be the other half of the story, and it is **not** done here:
it changes an allocation size and a register layout, and this repository does not land
hardware claims it has not run.

**Status: the amendment is HOST-VERIFIED ONLY.** It is build-clean at `W=1` and every
case in `expected-errno.tsv` plus MPP's own request shape was replayed against the
real class table on the workstation. It has not been on a board. The required next
step is a rebuild and a **cold-boot, no-fault control encode**.

**The generalisable lesson.** `0022` v1 passed every test written for it and broke
production anyway, because the tests were all *fault* cases and the thing it broke
was the happy path. A cold-boot control encode with nothing armed is what caught it,
and it should be a mandatory leg of **every** rkvenc UAPI change in this series, not
an occasional one — a green fault drill says nothing about whether the driver still
encodes.

---

`tests/rkvenc-invalid-ioctl.c --all-malformed` reported this against
`tests/expected-errno.tsv` on a real Rock 5B+, on the series through `0020`:

```
FAIL class-overrun:        expected EINVAL, got OK (0)
FAIL trans-table-odd-size: expected EINVAL, got OK (0)
FAIL bad-user-pointer:     expected EFAULT, got EIO (5)
FAIL valid-after-failures: expected OK,     got EINVAL (22)
ok   offset-size-wrap / undersized-word / unaligned-offset / invalid-metadata -> EINVAL
```

`0022` addresses the first three. **It does not address the fourth**, and the
reason matters more than the symptom, so it is written down here rather than left
for the next drill to rediscover.

**The four `ok` lines were passing for the wrong reason.** None of
`offset-size-wrap`, `undersized-word`, `unaligned-offset` or `invalid-metadata`
was being *rejected* by a bounds check. Each one produces a submission that
allocates no class-`PIC` register buffer, and `rkvenc_task_get_format()` opens
with `if (!class_reg || !class_size) return -EINVAL;` — because
`hw->fmt_reg.class` is `RKVENC_CLASS_PIC` and that is where the format bit lives.
So the expected `EINVAL` was arriving from a *format lookup*, several steps past
the check that should have produced it. `0022` makes all four fail at the point
that names them, which is the difference between a test that passes and a test
that means something. `invalid-metadata` in particular was reaching
`rkvenc_extract_reg_offset_info()` and being **accepted** — that function had no
whole-element check at all, so a 13-byte blob was copied as one whole 8-byte
element plus five bytes of the next.

**Why `valid-after-failures` is red, and why it is not a driver defect.** The case
issues one `MPP_CMD_SET_REG_WRITE` at `CLASS_BASE_S` for the whole of class
`BASE`, and asserts `OK`. That request is well formed, and after `0022` it passes
every bounds check — and then `rkvenc_task_get_format()` rejects it by exactly the
mechanism above: a submission that writes only class `BASE` allocates no class
`PIC` buffer, and the format register is in `PIC`. **The harness's "well-formed
request" is not a well-formed task.** Real `librockchip-mpp` always programs class
`PIC`; a task without it has no format, and `rkvenc2_setup_task_id()` immediately
after would dereference `task->reg[RKVENC_CLASS_PIC].data` unconditionally, so
`get_format()` returning `-EINVAL` there is load-bearing, not incidental.

Two possible readings, and the honest one is the second:

- *The driver should accept a partial register write.* It should not. The format
  drives FD translation and the DCHS id write; a task with no `PIC` class is not a
  task the hardware can be given.
- *The harness case should submit a complete task.* Yes — the fix is to add a
  second `MPP_CMD_SET_REG_WRITE` covering class `PIC` (`base_s = 0x0280`,
  `size = 0x03f4 - 0x0280 + 4`) alongside the existing class-`BASE` one.

That change is **deliberately not made here**, for a reason that is not
squeamishness: it changes what runs on the board. Today the case is rejected
before submission, so nothing is queued. A complete task *is* queued, reaches the
hardware with all-zero registers, and is retired by the watchdog and a hardware
reset. That is a real behavioural change to a drill, it cannot be verified from
source, and this repository does not land board-behaviour claims it has not run.
It is also not a new risk — `class-overrun` submits and runs exactly such a task
today, which is precisely why it returned `OK` — but the decision belongs to
whoever runs the next drill, with the board in front of them.

Until then: `valid-after-failures` is expected to stay red, `0022` is not the
reason, and a green `--all-malformed` is **not** the acceptance criterion for
either `0021` or `0022`. The criterion is the other seven cases plus the
`fail-clock-enable` transcript.

**Two bounds defects in this patch are not covered by any drill case**, and will
not be proven by re-running one: the `w_req_cnt`/`r_req_cnt` overflow needs two
class-spanning write messages in one ioctl, and the
`rkvenc_extract_reg_offset_info()` byte/element overrun needs `8*128 + 7` bytes of
offset metadata. Neither is in `expected-errno.tsv`. They were found by reading
the paths the failing cases run through, they are fixed on the strength of that
reading, and they stay `UNVALIDATED` in the strict sense — a KASAN board running
the existing drill will not exercise them. Adding two cases for them is the
obvious follow-up and is not done here, for the same reason as above: a new drill
case is a claim about a board.

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

## 2026-08 candidate reconciliation matrix (M1–M8 / U1–U7)

One screening round, fifteen candidates, one row each — **including the ones that
were excluded before a single command was run**. A candidate that leaves no row
reads later as a candidate nobody thought of, which is exactly the confusion this
ledger exists to prevent, so "not screened, and here is why" is recorded as a
result rather than omitted.

Discovery artifact: the Collabora `mainline-status.md` snapshot, fetched
`2026-08-09T20:27:03Z`, 27,159 bytes. The live `ref=main` bytes still matched that
digest when this round re-fetched them on 2026-08-10, and the same bytes are
reproducible from the immutable commit-pinned URL
`…/repository/files/mainline-status.md/raw?ref=8bcf0c0493a1bf90e4e7216e25a6b2a00a5688f8`,
which is recorded as the source of record so a later edit to the page cannot move
this round's ground truth.

**Screening base:** `v7.1.7` (`c7ba9d6de43e9d9bd755b1f3c19501a38898c6b6`), a real
checkout — `Apply base-only` and `Apply stacked` below are `git apply` results
against that tree, not judgements. **Build result** is a symbol-resolution and
`git am` result: this repository compiles nothing by design (see `AGENTS.md`
"Scope is patch application only"), so a row claiming a compile would be a claim
this repo cannot make. **Last checked: 2026-08-10** for every row.

**Machine-checked.** `scripts/validate-candidate-matrix.py` refuses this block if
an alias, a field or the snapshot digest is missing, empty, duplicated, or carries
a disposition outside `IN` / `OUT` / `ALREADY-IN-BASE / NO IMPORT` /
`ALREADY CARRIED`:

```bash
python3 scripts/validate-candidate-matrix.py docs/UPSTREAM-STATUS.md \
  --aliases M1,M2,M3,M4,M5,M6,M7,M8,U1,U2,U3,U4,U5,U6,U7 \
  --source-sha256 729b87afb5a4fb097713b79e264a3688e25f3f971a8b9fcbc6c73d49340dccb9
```

<!-- candidate-matrix: begin -->

Discovery snapshot sha256: 729b87afb5a4fb097713b79e264a3688e25f3f971a8b9fcbc6c73d49340dccb9

#### M1

- Capture revision: merged mainline commit, captured 2026-08-10
- Subject: mmc: sdhci-of-dwcmshc: check bus clock enable result in the probe() method
- Identity: commit `521f39ca93cc43ce1b3eae8d44201f8f55dd9151`
- Thread review: merged with `Acked-by: Adrian Hunter`, `Cc: stable@vger.kernel.org`, applied by Ulf Hansson; two `Fixes:` tags (`e438cf49b305`, `bccce2ec7790`)
- Prerequisite graph: none — the change is local to `dwcmshc_probe()` error unwinding
- Follow-up sweep: not needed; the commit is already present in the screening base, so any follow-up would arrive through 7.1.y like the commit itself did
- Apply base-only: forward `git apply --check` FAILS, reverse `git apply -R --check` SUCCEEDS on every hunk — the post-image is already the base
- Apply stacked: not attempted; a patch already present in the base cannot be stacked onto it
- Overlap: none with any series member; no member touches `drivers/mmc/`
- Build result: not applicable — nothing is imported, and the base already carries `err_bus_clk` at `sdhci-of-dwcmshc.c:2513` plus the checked `clk_prepare_enable(priv->bus_clk)` at 2443
- Regression state: none known; the fix is in the shipped base and has been through 7.1.y
- Retire trigger: not applicable — there is nothing carried to retire
- Disposition: ALREADY-IN-BASE / NO IMPORT

#### M2

- Capture revision: merged mainline commit (7.3-rc1 per the Collabora table), captured 2026-08-10
- Subject: phy: rockchip: naneng-combphy: Always configure SSC spread direction
- Identity: commit `be2b5b17b7053fee142939076746d26b2d6c9702`
- Thread review: merged with `Tested-by: Liu Changjie`, `Cc: stable`, `Fixes: 0b31f297557f`, applied by Vinod Koul
- Prerequisite graph: exactly one, and it is decisive — the commit only makes sense on top of `0b31f297557f` ("Consolidate SSC configuration"), which introduced the regression it repairs
- Follow-up sweep: `torvalds/linux` commits on `phy-rockchip-naneng-combphy.c` since 2026-03-25 are `0b31f297557f` (2026-05-19) and this commit (2026-07-20); neither is in `v7.1.7`
- Apply base-only: forward FAILS — the base has no `rk_combphy_common_cfg_ssc()` for the hunks to land in
- Apply stacked: not attempted; the base-only result already settles it
- Overlap: would overlap `0010` (both edit `phy-rockchip-naneng-combphy.c`), which is moot given the disposition
- Build result: not applicable — nothing imported
- Regression state: the regression this fixes does not exist in the base. `v7.1.7` still performs the `RK3568_PHYREG32` direction writes unconditionally inside each per-type `switch` (lines 604, 614, 759, 771, 885) and gates only the "Enable SSC" block on `priv->enable_ssc`, which is the pre-`0b31f297557f` behaviour this commit restores
- Retire trigger: not applicable — nothing carried. If the base ever absorbs `0b31f297557f` without this commit, re-open the candidate
- Disposition: OUT

#### M3

- Capture revision: merged mainline commit, captured 2026-08-10
- Subject: media: rockchip: rga: avoid odd frame sizes for YUV formats
- Identity: commit `92f50870ae987b8e2e5334e4ee38f82f6f405d78`
- Thread review: not read — excluded by the approved import tier before technical screening began
- Prerequisite graph: not resolved — excluded before screening
- Follow-up sweep: not run — excluded before screening
- Apply base-only: not attempted — excluded before screening
- Apply stacked: not attempted — excluded before screening
- Overlap: not assessed — excluded before screening; RGA is touched by no series member
- Build result: not run — excluded before screening
- Regression state: not assessed — excluded before screening
- Retire trigger: not applicable — nothing carried. Re-open only if the approved import tier is widened to RGA
- Disposition: OUT

#### M4

- Capture revision: merged mainline commit set, captured 2026-08-10
- Subject: Panthor runtime/reset/MMU/firmware stability set
- Identity: commits `e62179fd3e23ecfaedf7101e19ec0d3e4f51de76`, `1b8d771fb214e1f783d66caf13d35d7eda39a643`, `1f27cef1f41dac0bd254d8741766f189936c9880`, `b921b8613790a3f9e78ab64017fa7149ef0b750c`, `4a2c8cbe9bcba170706fdf08b1c84b6cbcf5b044`, `2b8f13d3c7e26c46c20d9e367904cf01729c88e6`
- Thread review: not read — excluded by the approved import tier before technical screening began
- Prerequisite graph: not resolved — excluded before screening. The set is six commits on its face, which is already past this lane's two-prerequisite ceiling
- Follow-up sweep: not run — excluded before screening
- Apply base-only: not attempted — excluded before screening
- Apply stacked: not attempted — excluded before screening
- Overlap: not assessed — excluded before screening; the GPU driver is touched by no series member
- Build result: not run — excluded before screening
- Regression state: not assessed — excluded before screening
- Retire trigger: not applicable — nothing carried. Re-open only if the approved import tier is widened to Panthor
- Disposition: OUT

#### M5

- Capture revision: `PATCHv2` posting, merged for 7.2-rc1 per the Collabora table; captured 2026-08-10
- Subject: media: synopsys: hdmirx: Fix HPD lane hold time — the Collabora table names this row "HDMI-RX EDID fix", which is the symptom, not the mechanism
- Identity: lore `20260325105742.63236-1-dmitry.osipenko@collabora.com`; the stable backport in the base is `7dd27810eea0`, itself the backport of mainline `d1162a5adbb5`
- Thread review: single message, `Signed-off-by: Dmitry Osipenko`, no objections in thread
- Prerequisite graph: none — a two-line `msleep(100)` → `msleep(100 + 50)` change in `hdmirx_hpd_ctrl()`
- Follow-up sweep: not needed; the change is already in the base via 7.1.6
- Apply base-only: forward `git apply --check` FAILS, reverse `git apply -R --check` SUCCEEDS — the post-image is the base. Verified against the real `v7.1.7` checkout, not inferred from `docs/EVAL-0002-EDID.md`
- Apply stacked: not attempted; a patch already present in the base cannot be stacked onto it
- Overlap: shares `snps_hdmirx.c` with `0002`/`0003`/`0005`, but shares no mechanism — `0002` is IRQ masking, lock-loop rework and DMA reset; this is HPD hold time
- Build result: not applicable — nothing imported
- Regression state: none known; in the base since `v7.1.6`
- Retire trigger: not applicable — nothing carried. This row exists so that a future reader does not re-import it. It is **not** a replacement for `0002`; see `docs/EVAL-0002-EDID.md`
- Disposition: ALREADY-IN-BASE / NO IMPORT

#### M6

- Capture revision: merged mainline commit, carried since the `0007` import; re-verified 2026-08-10
- Subject: iommu/rockchip: disable fetch dte time limit
- Identity: commit `8d4346ecd4950ae08cc76a6de327c264e846758c`, lore `20260428-spu-iommudtefix-v2-1-f592f579e508@pengutronix.de`
- Thread review: `Acked-by: Heiko Stuebner`, applied by Joerg Roedel; no `Fixes:` tag and no `Cc: stable`, which is why 7.1.y will not pick it up on its own
- Prerequisite graph: none — `RK_MMU_AUTO_GATING` and `rk_iommu_read/write` already exist in the base
- Follow-up sweep: unchanged since the `0007` import sweep; no landed follow-up on `rockchip-iommu.c` invalidates it
- Apply base-only: applies with no fuzz — this is what the existing `0007` import does today
- Apply stacked: `scripts/apply.sh` applies the full 12-member series to `v7.1.7`, `0007` included, on 2026-08-10
- Overlap: none — `0007` is the only member touching `drivers/iommu/`
- Build result: `git am` of the whole series succeeds; no unresolved symbol
- Regression state: none known
- Retire trigger: pinned base reaches `v7.2`, then retire through `retired/REGISTRY.md`
- Disposition: ALREADY CARRIED

#### M7

- Capture revision: `PATCHv3` posting, merged for 7.2-rc1 per the Collabora table; captured 2026-08-10
- Subject: Add support for I2S MCLK output gate clocks (RK3588)
- Identity: lore `20260320-rk3588-mclk-gate-grf-v3-0-980338eacd2c@superkali.me`
- Thread review: already read and written up in this document — see "I2S MCLK gate clocks — skipped, known regression on Rock 5B+"
- Prerequisite graph: four deep, recorded in that section; the lane's ceiling is two
- Follow-up sweep: not re-run — the recorded Rock 5B+ regression has no landed fix, which is the blocking finding and does not change with a sweep
- Apply base-only: not re-attempted — the decision is behavioural, not an apply result
- Apply stacked: not re-attempted, same reason
- Overlap: would touch the I2S/clock path `0006` depends on, which is precisely why the recorded Rock 5B+ regression is disqualifying here
- Build result: not run — the candidate is excluded on a recorded regression, not on build
- Regression state: documented Rock 5B+ regression with no landed fix. This is an owner decision already taken; it is not re-litigated here
- Retire trigger: not applicable — nothing carried. Re-open only if the recorded regression is demonstrably fixed upstream
- Disposition: OUT

#### M8

- Capture revision: `PATCHv2` posting, 13 patches, merged for 7.2-rc1 per the Collabora table; captured 2026-08-10 from the canonical thread archive
- Subject: arm64: dts: rockchip: Wire up frl-enable-gpios for RK3576/RK3588 boards
- Identity: lore `20260428-dts-rk-frl-enable-gpios-v2-0-924df9db884a@collabora.com`
- Thread review: cover plus 13 patches plus one reply; a clean, uncontested device-tree wiring series
- Prerequisite graph: the *driver* half is already in the base — `dw_hdmi_qp-rockchip.c` reads `frl-enable-gpios` at line 553 and the property is documented in `rockchip,rk3588-dw-hdmi-qp.yaml`. The series itself is 13 sequential patches, and patches 11–13 are unrelated `pinctrl-names` cleanup
- Follow-up sweep: not run — the disposition turns on payload scope, which no follow-up changes
- Apply base-only: the thread parses and the 13 patches extract cleanly; a full apply was not run because the candidate is excluded on scope
- Apply stacked: not attempted, same reason
- Overlap: patches 04 and 12 touch `rk3588-orangepi-5-plus.dts`, which `0006` also edits — a real overlap risk for a payload with no capture-path benefit
- Build result: not run — excluded on scope
- Regression state: none known upstream. Absent the GPIO the encoder falls back cleanly to TMDS, which the binding states explicitly, so declining costs no working behaviour
- Retire trigger: not applicable — nothing carried. Re-open if CeraLive ever ships HDMI **output** above 4K60, which needs FRL and therefore this bias wiring
- Disposition: OUT

#### U1

- Capture revision: `PATCHv3`, posted 2026-04-08; captured 2026-08-10 from the canonical thread archive
- Subject: mmc: sdhci-of-dwcmshc: Disable clock before DLL configuration
- Identity: lore `1775632729-22841-1-git-send-email-shawn.lin@rock-chips.com`
- Thread review: two messages — the posting (`Signed-off-by: Shawn Lin`, `Acked-by: Adrian Hunter`) and a reply from Ulf Hansson
- Prerequisite graph: depends on U2's Rockchip platform-data refactor, which is why U2 is ordered before U1 wherever both are considered
- Follow-up sweep: not needed; the change is already present in the base
- Apply base-only: forward FAILS, reverse `git apply -R --check` SUCCEEDS on every hunk
- Apply stacked: not attempted; already present in the base
- Overlap: none with any series member
- Build result: not applicable — nothing imported. The base carries the exact constructs the posting adds: `/* Disable clock while config DLL */` (line 787), the `enable_clk:` label (876) and `sdhci_enable_clk(host, 0)` (884)
- Regression state: none known
- Retire trigger: not applicable — nothing carried
- Disposition: ALREADY-IN-BASE / NO IMPORT

#### U2

- Capture revision: `PATCHv2`, posted 2026-03-27; captured 2026-08-10 from the canonical thread archive
- Subject: mmc: sdhci-dwcmshc: Refactor Rockchip platform data for controller revisions
- Identity: lore `1774620875-18258-1-git-send-email-shawn.lin@rock-chips.com`
- Thread review: two messages — the posting (`Signed-off-by: Shawn Lin`) and `Acked-by: Adrian Hunter`
- Prerequisite graph: none; it is itself U1's prerequisite
- Follow-up sweep: not needed; the refactor is already present in the base
- Apply base-only: forward FAILS and reverse FAILS, but only on one hunk, and the content check settles it — see Build result
- Apply stacked: not attempted; already present in the base
- Overlap: none with any series member
- Build result: not applicable — nothing imported. Every construct the refactor introduces is in the base: `struct rockchip_pltfm_data` (line 328) with its `revision` member (335), `to_pltfm_data(dwc_priv, rockchip)` (757), the `revision == 0` / `revision == 1` tests (828, 854) and the three `sdhci_dwcmshc_rk35xx_pdata` initialisers (2131, 2147, 2163). The reverse apply fails only because a later cosmetic change dropped a pair of parentheses at line 854
- Regression state: none known
- Retire trigger: not applicable — nothing carried
- Disposition: ALREADY-IN-BASE / NO IMPORT

#### U3

- Capture revision: `PATCHv1` (posted as a bare `[PATCH]`), 2026-03-25; captured 2026-08-10 from the canonical thread archive
- Subject: phy: rockchip: naneng-combphy: Fix TX detect RX termination errata
- Identity: lore `1774423383-36599-1-git-send-email-shawn.lin@rock-chips.com`
- Thread review: three messages — the posting (`Signed-off-by: Shawn Lin`), an author ping on 2026-04-27, and Vinod Koul on 2026-05-10 asking for a `Fixes:` tag and an erratum reference. Unanswered, no reroll, no `Reviewed-by`, no `Nacked-by`. The open question is about the commit message, not the register write
- Prerequisite graph: none — `rockchip_combphy_updatel()` and the `RK3568_PHYREG*` block are in the base, and `RK3568_PHYREG26` is defined by the patch itself
- Follow-up sweep: `phy-rockchip-naneng-combphy.c` took `0b31f297557f` (2026-05-19) and `be2b5b17b705` (2026-07-20) in mainline since the posting; neither is in `v7.1.7` and neither touches the RTERM path
- Apply base-only: applies with no fuzz to `v7.1.7`
- Apply stacked: applies with no fuzz on top of the existing series
- Overlap: none — no other series member touches `drivers/phy/`
- Build result: `git am` of the 12-member series succeeds; no unresolved symbol
- Regression state: none known; no reported regression on the thread
- Retire trigger: the posting merges AND the pinned base absorbs it — both, then retire through `retired/REGISTRY.md`
- Disposition: IN

#### U4

- Capture revision: `PATCHv5`, 10 patches, posted 2026-07-23; captured 2026-08-10 from the canonical thread archive
- Subject: phy: rockchip: samsung-hdptx: Clock fixes and API transition cleanups
- Identity: lore `20260723-hdptx-clk-fixes-v5-0-8e786067865f@collabora.com`
- Thread review: 31 messages. Manivannan Sadhasivam reviewed all ten on 2026-08-07 and gave `Reviewed-by` on eight — but asked for a behaviour change on 02/10 ("If the hardware state is invalid, why can't this be a hard failure?") and repeated it on 03/10, both unanswered
- Prerequisite graph: internally sequential — 03 and 06–10 fail a base-only apply on their own and only land after their predecessors, so taking any single fix means taking its chain
- Follow-up sweep: not decisive — the blocking finding is an open in-thread change request, which no mainline sweep can resolve
- Apply base-only: all ten apply with no fuzz **in sequence** to `v7.1.7`
- Apply stacked: not attempted — the candidate is excluded on review state, not on apply
- Overlap: none with any series member
- Build result: not run — excluded on review state
- Regression state: no reported regression; the exclusion is that 02 and 03 are still being negotiated
- Retire trigger: would not work. What merges will be a v6 whose 02/03 behave differently from what a v5 import would ship, so "retire when this merges" would silently stop matching — the same failure that turned away the fdinfo candidate
- Disposition: OUT

#### U5

- Capture revision: `PATCHv3`, standalone — **no cover letter and zero sibling patches**; posted 2026-05-21 by Simon Wright; captured 2026-08-10 from the canonical thread archive
- Subject: [PATCH v3] drm/bridge: dw-hdmi-qp: use drm_hdmi_acr_get_n_cts() helper for audio N/CTS
- Identity: lore `86fcf349-0a7a-4618-9001-612371b0f71b@symple.nz`
- Thread review: two messages — the posting (`Signed-off-by`, `Tested-by`, `Reported-by`, all Simon Wright) and Cristian Ciocaltea on 2026-06-03 giving `Reviewed-by` and `Tested-by` with "The patch looks good to me." No change requested, no reroll
- Prerequisite graph: none — `drm_hdmi_acr_get_n_cts()` is already exported by `drivers/gpu/drm/display/drm_hdmi_helper.c` in the base
- Follow-up sweep: the only mainline commit on `dw-hdmi-qp.c` since the posting is `fb145be7964d` (2026-05-21, common TMDS char rate constant), which does not touch the N/CTS path
- Apply base-only: applies with no fuzz to `v7.1.7`
- Apply stacked: applies with no fuzz on top of the existing series, and before `0012`
- Overlap: shares `dw-hdmi-qp.c` with `0012` and does not collide — this replaces the private N/CTS table, `0012` changes the audio enable/prepare hooks; applying `0011` then `0012` was verified clean in that order
- Build result: `git am` of the 12-member series succeeds; no unresolved symbol
- Regression state: none known
- Retire trigger: the posting merges AND the pinned base absorbs it — both, then retire through `retired/REGISTRY.md`
- Disposition: IN

#### U6

- Capture revision: `PATCHv1` (posted as a bare `[PATCH]`), 2026-05-19; captured 2026-08-10 from the canonical thread archive
- Subject: drm/bridge: dw-hdmi-qp: Return -EOPNOTSUPP in HDMI audio functions
- Identity: lore `20260519-fix-hdmi-audio-warnings-v1-1-9608966c993f@collabora.com`
- Thread review: five messages — the posting (`Signed-off-by: Detlev Casanova`), Sebastian Reichel asking only for a `Fixes: fd0141d1a8a2a` tag, `Tested-by: Maud Spierings` on an Orange Pi 5+ (2026-07-06), an author nudge (2026-08-06) and `Tested-by: Diederik de Haas` (2026-08-08) reporting hundreds of the errors it removes. No change to the payload was requested
- Prerequisite graph: none — two hunks, no new symbol
- Follow-up sweep: the only mainline commit on `dw-hdmi-qp.c` since the posting is `fb145be7964d` (2026-05-21), which does not touch the audio hooks
- Apply base-only: applies with no fuzz to `v7.1.7`
- Apply stacked: applies with no fuzz on top of the existing series and after `0011`
- Overlap: shares `dw-hdmi-qp.c` with `0011` and does not collide — see the `0011` row
- Build result: `git am` of the 12-member series succeeds; no unresolved symbol
- Regression state: none known; two independent `Tested-by` reports on RK3588 hardware
- Retire trigger: the posting merges AND the pinned base absorbs it — both, then retire through `retired/REGISTRY.md`
- Disposition: IN

#### U7

- Capture revision: `PATCHv6`, 4 patches, posted 2025-07-15; captured 2026-08-10 from the canonical thread archive
- Subject: PCI: Add support for resetting the Root Ports in a platform specific way
- Identity: lore `20250715-pci-port-reset-v6-0-6f9cce94e7bb@oss.qualcomm.com`
- Thread review: 25 messages, long-running cross-subsystem discussion; the b4 relay rewrites `From:` on some archived copies, which is why the importer records the observed senders beside the digest rather than inside it
- Prerequisite graph: unbounded for this base — the series was written against a mid-2025 tree and touches PCI core (`PCI/ERR`), `pci-host-common`, `pcie-qcom` and `pcie-dw-rockchip` together
- Follow-up sweep: not decisive — the candidate fails on apply before a sweep matters
- Apply base-only: 1/4 applies; **2/4, 3/4 and 4/4 all FAIL** in sequence — `pci-host-common.h:16`, `dwc/Kconfig:296` and `pcie-dw-rockchip.c:23` have all moved in `v7.1.7`
- Apply stacked: not attempted — a series that fails base-only cannot pass stacked
- Overlap: none with any series member
- Build result: not run — the series does not apply
- Regression state: not assessed — the candidate fails on apply
- Retire trigger: not applicable — nothing carried. Re-open only if the series is reposted against a 7.x tree
- Disposition: OUT

<!-- candidate-matrix: end -->

### Merged candidates: nothing was imported, and that is the result

Of the eight merged-side candidates, **none** produced an import, and each has a
different reason:

- **M1** and **M5** are already in `v7.1.7`. Both were checked against the real
  checkout rather than assumed: each reverse-applies cleanly with
  `git apply -R --check`, which only succeeds when every hunk's post-image is
  already the base. M1 carried `Cc: stable`, so 7.1.y picked it up; M5 arrived as
  `7dd27810eea0` at `v7.1.6`.
- **M6** has been carried as `0007` since its own import; it is verified, not
  re-imported.
- **M2** repairs a regression that the pinned base does not have. `v7.1.7` still
  writes the SSC spread direction unconditionally inside each per-type `switch`;
  the consolidation commit that broke it, `0b31f297557f`, is not in the base.
  Importing the fix would be importing a fix for nothing.
- **M8** is thirteen device-tree patches across roughly fifty boards, wiring an
  HDMI **output** FRL voltage-bias GPIO. The driver half is already in the base
  and the binding says an absent GPIO simply means TMDS-only, so declining costs
  no working behaviour on a capture appliance.
- **M3**, **M4** and **M7** were excluded by owner decision before technical
  screening; their rows record that as the finding rather than leaving a gap.

Row-by-row evidence is in the matrix above. The screening base was a real
`v7.1.7` checkout, and the apply results quoted there are `git apply` output.


### What the round changed

Three imports, all unmerged lore postings, all through
`scripts/import-lore-series.py` and none hand-transcribed: `0010` (U3), `0011`
(U5) and `0012` (U6). Ordinals continue after `0009`; the `0004` gap is untouched.

**No merged candidate was imported, and that is a result, not an omission.** M1 and
M5 are already in `v7.1.7` and were verified so against the real tree rather than
assumed; M6 has been carried as `0007` since its own import; M2 repairs a
regression the base does not have; M8 is out of scope; M3, M4 and M7 were excluded
by owner decision before screening.

**U1 and U2 are both already in the base**, so the "U2 before U1" prerequisite
order never becomes an import order. `scripts/check-series-ledger.py
--require-before U2:U1` still asserts it: the ordering must hold if both are ever
carried, and until then both must carry a recorded non-`IN` disposition rather
than simply be absent.

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
