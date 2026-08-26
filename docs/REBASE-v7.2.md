# Rebase ledger — CeraLive target `v7.1.7` → `v7.2`

This ledger records the move of the CeraLive RK3588 series from `v7.1.7` to
`v7.2`. The lane-scoped conflict law in `AGENTS.md` and `README.md` was amended
before any patch content changed.

| | |
|---|---|
| Previous base | `v7.1.7` = `c7ba9d6de43e9d9bd755b1f3c19501a38898c6b6` |
| **This base** | **`v7.2`**, tag object `237a1c39e8dfd3e1c6f1f023eea37a48ec04cc63`, commit `8d3ae59288f1e7d58d76558a6ee96d533bc5019f` |
| Rules file | [`rebase/v7.2.rules`](../rebase/v7.2.rules) |
| Active series | 22 members; slot total remains 27 |
| Retirement in this bump | `0007`, because `8d4346ecd495` is in `v7.2` |
| Result | **all 22 active members apply; `git am` exit 0; all post-apply assertions pass** |

## The lane-scoped rule

`rebase/*.rules` may alter context only, for every lane. At a base bump a
`ceralive/` patch may be revised in place to preserve its documented intent, but
each changed hunk is ledgered below. An `upstream/` or `backports/` payload is
never revised: behavioural drift there needs a fresh-ordinal `ceralive/` fixup or
the rebase stops. No such fixup or stop was needed at `v7.2`.

The boundary is enforced by `build-series.py`, which rejects a rule that resolves
to an added or removed line, and by `verify-payload-parity.py`, which compares the
generated payload with the current source-lane payload byte-for-byte.

## Human disposition table

The rc values are from sequential prefix-state probes. For each ordinal, the
final text of all preceding active members was already applied. The preimage is
the generated patch from `origin/main`, not a raw source-lane file.

| Ordinal | Lane | Verdict | pre fwd | pre rev | post fwd | Rule / revision | Finding |
|---|---|---:|---:|---:|---:|---|---|
| `0001` | upstream | KEEP | 0 | 1 | 0 | R1 | Existing RKVDEC1 context re-anchor remains necessary and sufficient. |
| `0002` | upstream | KEEP | 0 | 1 | 0 | — | Applies unchanged; `system_unbound_wq` remains declared at v7.2. |
| `0003` | upstream | KEEP | 0 | 1 | 0 | — | Applies unchanged. |
| `0005` | upstream | KEEP | 0 | 1 | 0 | R2 | Existing private-struct context re-anchor remains sufficient. |
| `0006` | ceralive | KEEP | 0 | 1 | 0 | — | HDMI-output/pinctrl DT churn does not overlap the HDMI-RX card hunks. |
| `0007` | retired | RETIRE | 1 | 0 | — | — | Reverse-applies because `8d4346ecd495` is already in the base. |
| `0008` | ceralive | KEEP | 0 | 1 | 0 | — | Applies unchanged. |
| `0009` | ceralive | ADAPT | 1 | 1 | 0 | A9.1–A9.7 | Revised in place for the modular system heap while preserving the uncached-heap contract. |
| `0010` | backports | KEEP | 0 | 1 | 0 | — | SSC refactoring changes neighbouring code only; posting applies unchanged. |
| `0011` | backports | KEEP | 0 | 1 | 0 | — | DRM atomic-state rename is outside this patch's audio helper hunks. |
| `0012` | backports | KEEP | 0 | 1 | 0 | — | Common TMDS-rate constant change is outside the no-mode audio return hunk. |
| `0013` | ceralive | KEEP | 0 | 1 | 0 | — | Applies unchanged. |
| `0014` | ceralive | KEEP | 0 | 1 | 0 | — | Applies unchanged. |
| `0015` | ceralive | KEEP | 0 | 1 | 0 | — | Applies unchanged. |
| `0016` | ceralive | KEEP | 0 | 1 | 0 | — | Applies unchanged. |
| `0017` | ceralive | KEEP | 0 | 1 | 0 | — | Applies unchanged. |
| `0018` | ceralive | KEEP | 0 | 1 | 0 | A18.1 | Code applies unchanged; its added note now cites v7.2's explicit no-unload statement. |
| `0019` | ceralive | KEEP | 0 | 1 | 0 | — | Applies unchanged. |
| `0020` | ceralive | KEEP | 0 | 1 | 0 | — | Applies unchanged. |
| `0021` | ceralive | KEEP | 0 | 1 | 0 | — | Applies unchanged. |
| `0022` | ceralive | KEEP | 0 | 1 | 0 | — | Applies unchanged. |
| `0026` | ceralive | KEEP | 0 | 1 | 0 | — | Applies unchanged. |
| `0027` | ceralive | KEEP | 0 | 1 | 0 | — | Applies unchanged. |

## Hunk-by-hunk ledger

### Context rules

#### R1 — `0001`, `rk3588-base.dtsi`, encoder-node insertion

The hunk adds the MPP service, CCU, and two encoder/MMU pairs between
`vdec1_mmu` and `av1d`. Its neighbouring power-domain anchor changed before the
previous base from `RK3588_PD_VDPU` to `RK3588_PD_RKVDEC1`. The five v7.2 DT
commits inspected for this bump reorder vdec registers and add RGA3, AV1 IOMMU,
CSI, and VICAP nodes; none changes an added encoder line or the
`vdec1_mmu`→`av1d` relationship. R1 replaces only that context line. All 15 hunks
then apply; the other 14 need no rule.

#### R2 — `0005`, `snps_hdmirx.c`, private-structure insertion

The six audio members remain immediately after `cec`; the mainline
`phy_rw_lock` remains between them and `stream_lock`. R2 inserts that one current
base line as context. The structure is private, unpacked, and accessed by member
name. All 18 hunks then apply; the other 17 need no rule.

### `0009` — v7.2 system-heap adaptation

`fd55edff8a0a` changed `DMABUF_HEAPS_SYSTEM` from bool to tristate and added module
metadata. `f7606400f19c` moved `system_cc_shared` under
`DMABUF_HEAPS_SYSTEM_CC_SHARED` and wrapped its paths in `cc_shared_buffer()`.
Those changes are real and require a first-party in-place revision. The intent is
unchanged: when enabled, a second heap named exactly `system-uncached` uses the
system allocator, non-cacheable mappings, one allocation-time clean, and skipped
CPU sync only for that heap.

| Hunk | File / area | Disposition and intent-preservation note |
|---:|---|---|
| 1 | `Kconfig` | **A9.1.** Re-anchor before `DMABUF_HEAPS_SYSTEM_CC_SHARED`; keep the new symbol bool and require `DMABUF_HEAPS_SYSTEM=y`, so the direct `arch_dma_prep_coherent()` call remains built-in and functional. |
| 2 | `system_heap.c` include | Keep: add `dma-map-ops.h`. |
| 3 | heap private data | Keep: add `uncached`. |
| 4 | exported-buffer data | Keep: add `uncached`. |
| 5 | attachment data | **A9.2.** Re-anchor before the new `cc_shared_buffer()` macro; still adds only the uncached flag. |
| 6 | attachment initialization | Keep: propagate the flag. |
| 7 | DMA map | **A9.3.** Preserve v7.2's `cc_shared_buffer(a)` expression, then OR `DMA_ATTR_SKIP_CPU_SYNC` only for uncached attachments. |
| 8 | DMA unmap | Keep: mirror the uncached map attribute. |
| 9 | begin CPU access | Keep: cached buffers still execute every sync. |
| 10 | end CPU access | Keep: cached buffers still execute every sync. |
| 11 | userspace mmap | **A9.4.** Preserve `cc_shared_buffer(buffer)` and independently apply `pgprot_writecombine()` only to uncached buffers. |
| 12 | kernel vmap | **A9.5.** Same independent treatment as mmap. |
| 13 | allocation local | Keep: read `priv->uncached`. |
| 14 | buffer initialization | Keep: store the flag. |
| 15 | allocation clean | **A9.6.** Re-anchor after v7.2's conditional CC-shared decryption; update the note to state why the `=y` dependency makes the unexported coherent-prep call valid. The clean itself is unchanged. |
| 16 | uncached private data | Keep: define the second heap's drvdata. |
| 17 | registration | **A9.7.** Register `system-uncached` after `system` and before v7.2's CC-shared early-return guard. This preserves both the new base's CC-shared policy and the userspace-visible uncached heap. |

### `0018` — truthful partial registration

All five mechanical hunks apply after the final `0009`: four registration/test
seam hunks in `system_heap.c`, then the new KUnit file. **A18.1** changes only the
added explanatory note and generated rationale: `fd55edff8a0a` explicitly says
the modular system heap cannot unload because the required infrastructure is
missing. Module loading changes when registration runs; it does not create a
rollback after the second `dma_heap_add()` fails. The tested partial-registration
semantics and all executable lines are unchanged.

### All other active members

Every hunk of the remaining active members applies as generated from the
pre-bump source: `0001` 15, `0002` 8, `0003` 2, `0005` 18, `0006` 5, `0008` 2,
`0010` 7, `0011` 3, `0012` 2, `0013` 18, `0014` 31, `0015` 11, `0016` 17,
`0017` 21, `0019` 7, `0020` 7, `0021` 36, `0022` 7, `0026` 5, and `0027` 5.
R1 and R2 are the only context rules. No `upstream/` or `backports/` byte changed.

## Patch-ID / content check against `v7.2`

Apply success was not treated as proof that a fix was still absent. The
sequential pre-probes reverse-failed for every active member, while content probes
confirmed the introduced driver directory, UAPI, DT labels, HDMI-RX symbols,
uncached heap, combphy erratum bit, dw-hdmi-qp helper behavior, and later
rkvenc/HDMI-RX hardening were not already present. `0007` was the sole opposite:
forward failed and reverse succeeded, matching its registry retirement because
`8d4346ecd495` is in the base.

The inspected drift inventory produced these independent results:

- `54eff31301a0`: real workqueue rename in existing HDMI-RX call sites. The only
  added `system_unbound_wq` reference is frozen `upstream/0002`; v7.2 still
  declares both `system_unbound_wq` and `system_dfl_wq`, and `0002` applies, so no
  `0028` fixup is justified.
- `0b31f297557f` + `be2b5b17b705`: real SSC refactoring/fix. `0010`'s RTERM
  register path remains separate and applies unchanged.
- `5164f7e7ff8e` + `fb145be7964d`: real DRM atomic-state and common TMDS-rate
  changes. Both frozen backports apply unchanged; no behavioural resolution is
  needed.
- `b481c11cd20`, `5052c99cf052`, `6ddfbec80077`, `25ee898961a2`, and
  `c7126247fb79`: real `rk3588-base.dtsi` churn, all outside the encoder payload;
  R1 is sufficient.
- `643d6733e58c` + `0c2c0b6cdd71`: real Orange Pi HDMI-output/pinctrl churn,
  outside `0006`'s HDMI-RX audio card and I2S enablement hunks.
- `fd55edff8a0a` + `f7606400f19c`: real modularization and CC-shared isolation;
  resolved by A9.1–A9.7 and A18.1.
- `hdmi-codec.c`: the prior “ZERO” claim was not literally true. Live path
  history found `9c61998c9c85`, a guard-based mutex refactor. No series member
  patches `sound/soc/codecs/hdmi-codec.c`, so it creates neither context nor
  payload drift.

## Stable overlap — `d1162a5adbb5`

Mainline `d1162a5adbb5` lengthens the HPD-low delay in
`hdmirx_hpd_ctrl()` from 100 ms to 150 ms. The GitHub comparison reports `v7.2`
21,100 commits ahead and zero behind that commit, with the commit itself as the
merge base. Against a clean `v7.2` tree its one-file diff gives:

```text
forward git apply --check: 1
reverse git apply --check: 0
git apply --3way --check: 0 (already applied cleanly)
```

`0002` does not rewrite that function. It adds call sites, IRQ exclusion around
EDID replacement, delayed hotplug work, lock-loop retries, DMA reset, and timing
constants. Its preimage forward-applies and reverse-fails in the prefix state.
The mechanisms still stack, and source alone still cannot answer whether `0002`
is redundant on hardware; the existing hardware-gated retirement question stays
open rather than being invented as a rebase resolution.

## Stopped for behavioural judgement

**None.** No frozen-lane payload drift was found. No new fixup ordinal and no
additional retirement were needed.

## Verification and compile evidence

`scripts/apply.sh` applies all 22 members to a clean checkout of the pinned v7.2
commit and passes every post-apply assertion. The machine-readable pre/post rc
record is in the v72-rebase disposition evidence.

Compile evidence: see the v72-rebase evidence bundle.

This ledger does not itself claim v7.2 board validation. The compile proof is the
next plan step, and board evidence recorded against v7.1.7 remains historical.
