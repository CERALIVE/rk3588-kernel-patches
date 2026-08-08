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

The series has five members. `0004` is a deliberate ordinal gap — upstream never
published one — and is not a row here for the same reason it is not a patch.

| Patch | Origin | Upstream status | Retire trigger | Last checked | Notes |
|---|---|---|---|---|---|
| `0001` vepu580 encoder (v3) | `upstream/` lane — imported from [`rcawston/rockchip-rk3588-mainline-patches`](https://github.com/rcawston/rockchip-rk3588-mainline-patches) @ `e13a311`; ported from the Rockchip BSP MPP driver. Upstream Linux counterpart: **N/A** | `WIP` — Collabora's rkvenc work, tracked at <https://lore.kernel.org/r/082e1141c38205222a91abf13b1a97d9a00e117a.camel@collabora.com> | **None foreseeable — track only.** Do *not* retire when rkvenc lands: see [§ 0001](#0001--do-not-retire-on-rkvenc-landing) | 2026-08-08 | Collabora table: VEPU580 H.264 = `WIP`, H.265 = `TODO` |
| `0002` hdmirx EDID fix (v1) | `upstream/` lane — Ross Cawston, same import. Upstream counterpart exists and is **different work**: "HDMI-RX EDID fix", PATCHv2, <https://lore.kernel.org/r/20260325105742.63236-1-dmitry.osipenko@collabora.com> | `merged@7.2-rc1` (the counterpart) | Base ≥ `v7.2` **and** a passing content check **and** T10's written verdict. Not automatic | 2026-08-08 | **Read [§ 0002](#0002--two-upstream-answers-one-unresolved-question) before evaluating.** `7dd27810eea0` (in the base since `v7.1.6`) already lands *an* upstream answer to the same symptom |
| `0003` hdmirx plugout fix (v1) | `upstream/` lane — Ross Cawston, same import. Upstream counterpart: **N/A** — none found (see [§ Sources](#sources-checked-for-this-sweep)) | `fork-carried-no-upstream` | None defined. Re-check at every base bump via the content check in [`REBASE-v7.1.7.md` § Patch-ID / content check](REBASE-v7.1.7.md#patch-id--content-check-against-the-new-base); retire only if a tree absorbs the `vb2_queue_error` plugout fix | 2026-08-08 | Content check at `v7.1.7`: `vb2_queue_error` still absent under `synopsys/hdmirx/` |
| `0005` hdmirx audio | `upstream/` lane — Ross Cawston, same import. Upstream counterpart: "HDMI Input → Audio", PATCHv4, <https://lore.kernel.org/r/20260721064115.64809-1-royalnet026@gmail.com> | `sent-v4` — posted, **not merged** | Counterpart merges **and** base reaches that version **and** T11's verdict adopts it **and** the `0006` pairing is resolved. All four | 2026-08-08 | Collabora table row "HDMI Input – Audio" = `sent`. Retiring `0005` without settling `0006` produces a bound codec and no ALSA card |
| `0006` hdmirx audio sound card | `ceralive/` lane — **first-party CeraLive**. Never submitted (no `Signed-off-by`, deliberately — see [`PROVENANCE.md` §8](PROVENANCE.md#8-first-party-patches-ceralive)). Upstream counterpart: **N/A** | `first-party-no-upstream` | Only if an upstream HDMI-RX audio series lands its **own** DT sound card for Rock 5B+ *and* Orange Pi 5+. T11 must answer this explicitly | 2026-08-08 | Modelled on the BSP's `hdmiin-sound` wiring, expressed with mainline `simple-audio-card`; no BSP text copied |

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

### `0002` — two upstream answers, one unresolved question

This is the one row that must not be read quickly.

**Fact 1 — an upstream EDID fix is merged for 7.2-rc1.** The Collabora capture
lists "HDMI-RX EDID fix (7.2-rc1)", PATCHv2 by Dmitry Osipenko:
<https://lore.kernel.org/r/20260325105742.63236-1-dmitry.osipenko@collabora.com>.
That is the counterpart T10 is chartered to evaluate `0002` against.

**Fact 2 — stable *already* shipped a different fix for the same symptom, and it
is in our base.** The T7 rebase found exactly one commit in the whole 744-commit
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

**Consequence for T10.** T10 evaluates `0002` against the 7.2-rc1 counterpart —
but there are now *two* upstream answers in play, and they have not been shown to
be the same work: `7dd27810eea0` / `d1162a5adbb5` is an HPD-hold-time change
reported in February, while the 7.2-rc1 series is Osipenko's March posting. T10's
evaluation therefore has to disambiguate them before comparing anything, and it
inherits the hardware gate on the "+50 ms is enough" question — a KEEP verdict
reached without a board is the honest outcome, not a failure. The standing bar
also applies: the in-house `0002` is reported to work well, so the threshold for
replacing it is high and the verdict must say so.

---

## Import and evaluation candidates (T10–T13)

Seeded 2026-08-08 from the Collabora capture and the plan text. **These are
candidates, not commitments** — each row is filled in by the task that owns it,
and a documented *skip* is a valid outcome for every one of them.

| Candidate | Owning task | Origin | Upstream status | Retire trigger | Last checked | Notes |
|---|---|---|---|---|---|---|
| HDMI-RX EDID fix (upstream counterpart to `0002`) | T10 | <https://lore.kernel.org/r/20260325105742.63236-1-dmitry.osipenko@collabora.com> (PATCHv2) — mainline commit SHA **not yet resolved** | `merged@7.2-rc1` | If adopted: retire the backport when base ≥ `v7.2`. If not adopted: row records the rejection reason | 2026-08-08 | Adoption *replaces* `0002`. Must first disambiguate from `7dd27810eea0` — see [§ 0002](#0002--two-upstream-answers-one-unresolved-question) |
| HDMI Input Audio PATCHv4 (upstream counterpart to `0005`) | T11 | <https://lore.kernel.org/r/20260721064115.64809-1-royalnet026@gmail.com> | `sent-v4` — not merged; claims-quality, thread review status to be recorded | If adopted: retire when merged upstream **and** base reaches that version | 2026-08-08 | Verdict MUST state whether `0006` stays required, needs adaptation, or is superseded |
| IOMMU "disable fetch dte time limit" | T12 | <https://lore.kernel.org/r/20260428-spu-iommudtefix-v2-1-f592f579e508@pengutronix.de> (PATCHv2) — mainline commit SHA to be resolved at import | `merged@7.2-rc1` | **Drop when base ≥ `v7.2`** | 2026-08-08 | `backports/` lane, `commit <sha> upstream.` provenance required. Skip-and-record if `7.1.y` already absorbed it, or if the prereq chain exceeds 2 commits |
| I2S MCLK output gate clocks | T12 | <https://lore.kernel.org/r/20260320-rk3588-mclk-gate-grf-v3-0-980338eacd2c@superkali.me> (PATCHv3) — mainline commit SHA to be resolved at import | `merged@7.2-rc1` | **Drop when base ≥ `v7.2`** | 2026-08-08 | Same lane and same skip conditions as the row above |
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
| The pinned kernel tree at `v7.1.7` | Path + content checks per patch | [`REBASE-v7.1.7.md` § Patch-ID / content check](REBASE-v7.1.7.md#patch-id--content-check-against-the-new-base) — 0 of 5 absorbed |

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
