# rk3588-kernel-patches

## ROLE IN THE GROUP

Holds the **mainline-track RK3588 kernel patch series** for CeraLive: VEPU580
hardware encoder plus three HDMI-RX fixes imported from upstream, one backported
IOMMU fix, three backported **unmerged lore postings** (a combphy erratum and two
dw-hdmi-qp audio fixes), and three first-party patches — the device-tree half that
makes HDMI-RX audio actually capturable, a DMA segment-size fix to the encoder
driver, and the `system-uncached` dma-heap the Rockchip MPP userspace requires by
name — converted to a `git am` mailbox series and pinned to an exact kernel tag.

Produces **patch text only** — no `.deb`, no kernel, no image artifact. It is
therefore **NOT in the device image `REPOS` array** and has **no `versions.yaml`
pin**, for the same reason `ceralive-infra` has none: there is nothing for the
image pipeline to fetch.

Relates to:
- `image-building-pipeline/` — the intended downstream consumer. A future
  kernel-build-from-source stage sources `kernel-pin.env` for the exact tag. The
  **shipped** image is unaffected (see KEY FACTS).
- `cerastream/` — the encoder this series enables is the mainline-track
  alternative to the vendor MPP path cerastream uses today.

Upstream: GitHub fork of
[`rcawston/rockchip-rk3588-mainline-patches`](https://github.com/rcawston/rockchip-rk3588-mainline-patches),
imported at `e13a311` (2026-07-01).

## STRUCTURE

```
rk3588-kernel-patches/
├── kernel-pin.env             # SINGLE SOURCE OF TRUTH for every pinned coordinate
├── upstream/                  # SOURCE LANE — Ross Cawston's raw diff -ruN files, VERBATIM + README.MD
├── ceralive/                  # SOURCE LANE — FIRST-PARTY raw diffs with no upstream counterpart
├── backports/                 # SOURCE LANE — externally-sourced patches, each carrying its OWN provenance
│   └── lore/<alias>/          # canonical mail of each UNMERGED posting, so its digest is recomputable offline
├── retired/                   # ARCHIVE — patches moved out of the series, byte-unchanged
│   └── REGISTRY.md            # the RETIRED registry: state machine + the retirement table
├── patches/                   # GENERATED git-am series + series file — NEVER hand-edit
├── overlays/                  # rockchip-rk3588-rkvenc-mpp.dts, verbatim
├── rebase/<tag>.rules         # per-kernel-tag context re-anchors (context lines ONLY)
├── scripts/
│   ├── preflight.sh           # re-resolve the Armbian edge mapping; --head for live check
│   ├── build-series.py        # source lanes -> patches/ ; --check asserts in-sync; orphan check
│   ├── verify-payload-parity.py  # proves patches/ changes nothing its source lane didn't
│   ├── import-lore-series.py  # the ONLY sanctioned way to import an unmerged posting
│   ├── validate-candidate-matrix.py  # every screened candidate has every field
│   ├── check-series-ledger.py # SERIES <-> patches/ <-> UPSTREAM-STATUS.md, compared exactly
│   └── apply.sh               # the gate: verify -> clone pinned tag -> git am -> assert
├── tests/                     # stdlib unittest fixtures for the Python tooling
├── docs/
│   ├── UPSTREAM-STATUS.md     # per-patch upstream status + retire-on-merge triggers
│   ├── BOARD-QUALIFICATION.md # the DEFERRED hardware checklist — every item unchecked, by design
│   ├── EVAL-0002-EDID.md      # verdict: keep 0002; the 7.2-rc1 fix is already in the base
│   ├── EVAL-0005-AUDIO.md     # verdict: keep 0005+0006; the lore v4 series drops Rock 5B+
│   ├── PROVENANCE.md          # licence/provenance audit incl. the MIT-claim caveat
│   ├── PREFLIGHT.md           # how the Armbian edge -> 7.1 mapping was derived
│   ├── REBASE-v7.1.7.md       # hunk-by-hunk rebase ledger — CURRENT base; the 5 re-anchored members (0007/0008/0009 needed none)
│   └── REBASE-v7.1.5.md       # ledger for the previous base, kept for the record
└── .github/workflows/patch-apply.yml
```

## WHERE TO LOOK

| Task | Location |
|------|----------|
| Change the target kernel | [`kernel-pin.env`](kernel-pin.env) + a new `rebase/<tag>.rules` + a new `docs/REBASE-<tag>.md` |
| Add a CeraLive-authored patch | `ceralive/<NNNN>-*.patch` + a `SERIES` entry with `origin=CERALIVE` in `scripts/build-series.py`, then regenerate |
| Add a patch taken from a MERGED mainline commit | `backports/<NNNN>-*.patch` + a `SERIES` entry with `origin=BACKPORTS` **and** a `Backport(...)` — see [`backports/README.md`](backports/README.md) |
| Add a patch taken from an UNMERGED lore posting | run `scripts/import-lore-series.py`, then a `SERIES` entry with `origin=BACKPORTS`, `provenance=LORE_POSTING` **and** a `LorePosting(...)` — see [`backports/README.md`](backports/README.md) |
| Whether a screened candidate was taken, and why | [`docs/UPSTREAM-STATUS.md`](docs/UPSTREAM-STATUS.md) § 2026-08 candidate reconciliation matrix |
| Whether a patch has an upstream counterpart / can be dropped yet | [`docs/UPSTREAM-STATUS.md`](docs/UPSTREAM-STATUS.md) |
| What a real board must demonstrate before an `UNVALIDATED` marker comes off | [`docs/BOARD-QUALIFICATION.md`](docs/BOARD-QUALIFICATION.md) |
| Why the `system-uncached` heap exists, and why its NAME is not negotiable | [`docs/UPSTREAM-STATUS.md`](docs/UPSTREAM-STATUS.md) § `0009` and `patches/0009-*`'s own mail header |
| Why `0002` was kept instead of taking the upstream EDID fix | [`docs/EVAL-0002-EDID.md`](docs/EVAL-0002-EDID.md) |
| Why `0005`+`0006` were kept instead of taking the lore HDMI-audio series | [`docs/EVAL-0005-AUDIO.md`](docs/EVAL-0005-AUDIO.md) |
| Stop carrying a patch | **Never `git rm` it.** Move it to `retired/` and add a row — see [`retired/REGISTRY.md`](retired/REGISTRY.md) |
| Why HDMI-RX audio needs a DT patch at all | [`docs/PROVENANCE.md`](docs/PROVENANCE.md) §8 and `patches/0006-*`'s own mail header |
| Why the rkvenc DMA segment-size fix exists, and why the IOVA guardrail is left alone | [`docs/UPSTREAM-STATUS.md`](docs/UPSTREAM-STATUS.md) § `0008` and `patches/0008-*`'s own mail header |
| Check whether Armbian moved `edge` | `scripts/preflight.sh --head` |
| Understand the 7.1 derivation | [`docs/PREFLIGHT.md`](docs/PREFLIGHT.md) |
| Apply the series | `scripts/apply.sh` — see [`README.md`](README.md) |
| Why a hunk was re-anchored | [`docs/REBASE-v7.1.7.md`](docs/REBASE-v7.1.7.md) |
| Licence / redistribution facts | [`docs/PROVENANCE.md`](docs/PROVENANCE.md) |
| Why not the `sfqr0414` fork | [`README.md`](README.md) → "Why not the `sfqr0414` fork" |

## KEY FACTS

**`patches/` is generated. Editing it by hand is a bug, and CI catches it.**
`scripts/build-series.py --check` regenerates from `upstream/` + `ceralive/` into a
temp dir and byte-compares. Change a source lane or `rebase/<tag>.rules`, then
regenerate — never the other way round.

**Three source lanes, one pipeline: `upstream/` is imported, `ceralive/` is ours,
`backports/` is everyone else's.** `upstream/` must stay byte-identical to Ross
Cawston's published files forever — that is what makes the credit line, the licence
audit and the parity claim checkable. A patch CeraLive authors goes in `ceralive/`
and continues the same numbering (`0006` and up). A patch lifted from mainline, a
stable tree or a lore posting goes in `backports/`. All three lanes run through
`build-series.py`, get the same context-only rebase discipline, and are held to the
same added/removed-line parity by `verify-payload-parity.py` — the lane only changes
which mail header is written and which directory parity is proven against. **Never
put first-party or backported content in `upstream/`.**

**An UNMERGED posting never gets a commit id, and this is the repository's
sharpest correctness rule.** `backports/` has two provenance variants. A merged
commit carries `Backport(...)` and a 40-hex `provenance`, and its header says
`commit <sha> upstream.`. An unmerged lore posting carries `LorePosting(...)` and
`provenance=LORE_POSTING`, and its header says `Backport of unmerged <vN>
posting.` and nothing else — **no `commit <sha> upstream.`, no `NULL_OID`, no
parent SHA, no 40-hex mbox delimiter.** `NULL_OID` is the trap: it is forty hex
digits, so it passes every shape test while asserting the patch came from the null
commit. There is no identity to state, so the header states its absence.
`scripts/check-series-ledger.py` fails the build if one ever appears, and
`build-series.py` refuses an entry carrying both variants or neither. Importing is
`scripts/import-lore-series.py`'s job only: it requires the canonical
`all/<msgid>/t.mbox.gz`, treats patchwork and `/r/<msgid>/raw` as discovery
instruments that may justify an OUT verdict but never supply bytes, and a blocked
archive means OUT `unfetchable-canonical-thread` rather than a hand-typed patch.
Details, digest domains and the refusal list: [`backports/README.md`](backports/README.md).

**`backports/` carries provenance per patch, because it cannot inherit one.** The
`upstream/` lane hard-codes a single credit block — *"Imported from
`UPSTREAM_PATCHES_REPO` at `UPSTREAM_PATCHES_REV` … Authored by Ross Cawston"* —
which is true of every file in that directory and of nothing else. So every
`backports/` member must name its own origin: `provenance` is the 40-hex commit it
is backported from (never `NULL_OID`, which is 40 hex digits and would otherwise
pass the shape test), and a `Backport(upstream_subject=…, lore_msgid=…, note=…)`
supplies the rest. The generated header emits the stable-tree
`commit <sha> upstream.` marker plus a `https://lore.kernel.org/r/<msgid>` link.
The build refuses a `backports/` entry that lacks any of it.
Details: [`backports/README.md`](backports/README.md).

**Retirement, not deletion — `retired/` + a registry row is the ONLY way out.**
Deleting a source file would make "`upstream/` is byte-identical to what was
imported" unfalsifiable: a reviewer cannot tell "upstream published four" from
"someone quietly dropped the fifth". So a patch that stops being carried is **moved
byte-unchanged** into `retired/` and gains a row in
[`retired/REGISTRY.md`](retired/REGISTRY.md) — a Markdown table that is the doc and
the machine input at once, the same choice `rebase/*.rules` makes, so there is no
second copy to drift. Reinstating is the reverse: move back, restore the entry with
its **original** ordinal, drop the row. Retired ordinals are never reused, exactly
as the `0004` gap is never closed.

**Every patch's upstream position is tracked, and the retire trigger is written
down before it fires.** [`docs/UPSTREAM-STATUS.md`](docs/UPSTREAM-STATUS.md) holds
one row per series member and per pending import candidate: origin, upstream status
(`merged@<version>` / `sent-vN` / `WIP` / no-counterpart), the precondition for
dropping it, and the date that was last verified. Two traps it exists to prevent.
First, **a patch that still applies proves nothing** — upstream may already have
fixed the same thing, and only a content check says so. Second, **the trigger is a
precondition, not a licence to delete**: when it fires the patch still goes through
[`retired/REGISTRY.md`](retired/REGISTRY.md). Every lore reference in that file uses
`https://lore.kernel.org/r/<message-id>`, which resolves regardless of list; do not
record list-scoped URLs. Its Collabora source table sits behind an Anubis
proof-of-work gate, so re-capturing it needs a real browser, not `curl`.

**`0002` has exactly ONE upstream answer, we already ship it, and it is not a
replacement.** `7dd27810eea0` ("hdmirx: Fix HPD lane hold time", in the base since
`v7.1.6`) **is** the 7.2-rc1 "HDMI-RX EDID fix" — it is the stable backport of
mainline `d1162a5adbb5`, which is what the Collabora table's EDID row actually
points at. They are not two efforts; the table names the symptom while the patch
names the mechanism. It applies to `v7.1.7` as a **no-op**, and its 2-line HPD-hold
change shares no mechanism with `0002`'s IRQ masking, lock-loop rework and DMA
reset, so there is nothing to adopt and nothing to retire. Whether `0002` is still
*needed* on top of it remains a behavioural judgement that needs an RK3588 board
and an HDMI source — do not resolve that from the source alone. Verdict and
evidence: [`docs/EVAL-0002-EDID.md`](docs/EVAL-0002-EDID.md); see also
[`docs/UPSTREAM-STATUS.md`](docs/UPSTREAM-STATUS.md) § `0002` and
[`docs/REBASE-v7.1.7.md`](docs/REBASE-v7.1.7.md) § Stable overlap.

**Resolving a lore Message-ID does not need a browser — but try both routes.**
`lore.kernel.org`'s HTML views and its `/raw` endpoint are Anubis-gated (`curl`
gets 403 or a proof-of-work page). Two ways through, and neither covers every
posting on its own:

1. `patchwork.kernel.org` — `…/api/patches/?msgid=<msgid>` returns the real
   subject, submitter and project as JSON, and `…/patch/<msgid>/mbox/` returns
   the full posting including its changelog. Pair it with the GitHub
   commit-search API over `torvalds/linux` to get the mainline SHA. This is how
   the `0002` verdict resolved its counterpart. **It is not exhaustive:**
   patchwork returned zero results for the `0005` counterpart's Message-ID.
2. `https://lore.kernel.org/all/<msgid>/t.mbox.gz` — the gzipped **thread** mbox
   is served to a plain `curl` with no gate. It is strictly better when what you
   need is the *review*: it carries every patch in the series plus every reply,
   so `Reviewed-by` / `Tested-by` trailers, maintainer pushback and bot findings
   all come down in one fetch. Split it with Python's `mailbox`, dedupe by
   Message-ID (the archive returns each message twice), and un-escape mboxrd
   (`^>(>*From )` → `\1`) before feeding anything to `git apply`. This is how the
   `0005` verdict read its counterpart.

The Anubis-vs-browser note above still applies to the Collabora **table**, which
has no API of either kind.

**Membership is exactly-once, both directions, and the build enforces it.**
`build-series.py` used to walk a hard-coded `SERIES` table and never look at the
directories, so a new file dropped into `upstream/` or `backports/` was a silent
no-op. Now every `*.patch` under a source lane must be **either** an active `SERIES`
member **or** a registered retirement — never both, never neither. A registry row
with no archived file, an archived file with no row, a file present in two lanes,
a duplicate `SERIES` entry, and a reused ordinal all fail the build.
`verify-payload-parity.py` re-derives the same orphan check from the filesystem
alone, so the two opinions stay independent.

**Upstream's `git am` instruction has never worked — that is why this fork exists.**
The upstream files are raw `diff -ruN aa/ bb/` output with **no mail headers**, so
`git am` fails format detection before reading a hunk. `0001` and `0003` also carry
9 macOS `.DS_Store` `Binary files … differ` stanzas, which `git apply` refuses
("cannot apply binary patch … without full index line") even once headers exist.
`build-series.py` fixes both. Any instruction this repo publishes is executed
verbatim by CI, so it cannot rot the same way.

**Upstream numbering is preserved, gap included: `0001`, `0002`, `0003`, `0005`.**
There is no `0004` upstream. **Do NOT renumber to close the gap** — the 1:1 filename
correspondence with upstream is what makes the import auditable. First-party and
backported patches continue the same counter (`0006`, `0008` and `0009` =
`ceralive/`; `0007`, `0010`, `0011` and `0012` = `backports/`), so the ordinals
read `1/12`, `2/12`, `3/12`, `5/12` … `12/12` — the gap at 4 stays visible, which
is the whole point.

**`0005` is driver-only; `0006` is what makes HDMI-RX audio reachable.** Upstream's
`0005` registers an ASoC `hdmi-audio-codec` child under `hdmi_receiver@fdee0000`
and drives the receiver's audio FIFO/ACR/clock, but touches no device tree, and
ALSA does not create a card for a bare codec. On a Rock 5B+ running only `0001`–
`0005` the codec device is *bound* with no cable attached while `/proc/asound/cards`
shows no HDMI-RX capture card at all. `0006` supplies the three missing DT facts:
`#sound-dai-cells` on `hdmi_receiver`, an `hdmirx-sound` `simple-audio-card`, and
`&i2s7_8ch` + `&hdmirx_sound` enabled on the two CeraLive boards. `apply.sh` asserts
all of them post-apply, per board, because the failure mode is silent — everything
probes, nothing errors, there is simply no capture device.

**The upstream HDMI-audio series does NOT supersede `0006` — it would break the
pairing.** There is a real, fully-reviewed lore series
(<https://lore.kernel.org/r/20260721064115.64809-1-royalnet026@gmail.com>,
`[PATCH v4 0/4]`, Igor Paunovic) that does what `0005` does *and* carries its own
DT patches, so it looks at first glance like it retires both of ours. It does not,
for one blunt reason: its 4/4 is titled *"enable HDMI RX audio capture on Orange
Pi 5 Plus"* and enables the card on that board **only**. Rock 5B+ — the other
board in `ARMBIAN_BOARDS` — gets nothing, which is exactly the bound-codec-no-card
state above. The two DT halves also cannot coexist: `0006` and its 3/4 edit the
same two regions of `rk3588-extra.dtsi` and disagree on the cell arity
(`#sound-dai-cells = <0>` vs `<1>`), so `git apply --check` of `0006` onto an
upstream-applied tree fails outright. The series is otherwise adoptable — all four
patches apply clean to `v7.1.7` — and it is still declined, because it also drops
multichannel handling, jack reporting and `hdmirx_plugout()` teardown. Full
six-criteria verdict: [`docs/EVAL-0005-AUDIO.md`](docs/EVAL-0005-AUDIO.md). Do not
re-open this on the strength of "but it's upstream-shaped" — re-open it when the
series is *merged* and Rock 5B+ is covered.

**`0008` fixes `0001`, is marked `UNVALIDATED`, and does NOT make the edge-track
encoder work.** `rkvenc_dma_import_fd()` records an imported dma-buf's length as
`sg_dma_len(sgt->sgl)` — the FIRST mapped segment only — and `0001` never set a max
segment size, so `dma_get_max_seg_size()` answered the `SZ_64K` default, iommu-dma's
`__finalise_sg()` stopped coalescing there, and every import over 64 KiB was recorded
as exactly `0x10000` bytes. `0008` sets the cap in `rkvenc_hw_probe()` and **reads it
back**, failing the probe with `-EINVAL` if it did not take — at `v7.1.7`
`dma_set_max_seg_size()` returns `void`, so checking the effect is the only check
available and is the stronger one anyway.

Two things about it are easy to get wrong:

- **The IOVA guardrail in `rkvenc_service.c` is deliberately NOT touched, and must
  stay that way.** It was correct every time it fired: with the window truncated to
  64 KiB, an NV12 chroma-plane offset really is outside `[iova, iova+len)`. Silencing
  it hides the defect and trades a clean `-EINVAL` for a DMA write past the end of a
  mapping. `0008` touches exactly one file (`rkvenc_hw.c`).
- **This is one of THREE stacked defects.** The other two — `librockchip-mpp`
  hard-coding a `system-uncached` dma-heap mainline does not register, and mainline
  having no uncached heap to fall back to — are answered in source by `0009`, which
  is **also `UNVALIDATED`**. So all three defects now have a source-level fix and
  **none** has a hardware one: `0008` is necessary, `0008`+`0009` is plausibly
  sufficient, and neither claim has been observed on a board. Do not describe MPP
  hardware encode as fixed on the `edge` track. Full three-defect analysis: the CeraLive `image-building-pipeline`
  `AGENTS.md` KNOWN ISSUE "MPP hardware video encode does not work on the edge
  kernel". Marker and clearing conditions:
  [`docs/UPSTREAM-STATUS.md` § `0008`](docs/UPSTREAM-STATUS.md#0008--unvalidated-and-what-that-does-and-does-not-mean).

**`0009` is defects 1+3 of the same three, is `UNVALIDATED`, and its NAME is a
userspace ABI.** `librockchip-mpp` picks a dma-heap by hard-coded name and asks for
`system-uncached`, which mainline does not register — so the H.264 HAL's init-time
allocation fails and `mpph264enc` never registers as a GStreamer element at all
(defect 1). And because MPP does no CPU cache maintenance on a heap it believes is
uncached, cached memory under that name produces different output for identical
input plus intermittent CABAC failures (defect 3). `0009` registers a second heap
out of `system_heap.c` using the per-heap drvdata mechanism the file already has
for `system_cc_shared`: `pgprot_writecombine()` mappings, one `arch_dma_prep_coherent()`
clean at allocation (because `__GFP_ZERO` dirties the lines), and
`DMA_ATTR_SKIP_CPU_SYNC` plus skipped `dma_sync_sgtable_*` **only** for that heap.

Four things about it are easy to get wrong:

- **The heap name must be exactly `system-uncached`.** It is the entire userspace
  contract and there is no override in the shipped `librockchip-mpp1 1.5.0-1`. A
  typo is silent — a node appears, under a name nothing opens. `apply.sh` asserts
  the literal for that reason.
- **A symlink / bind-mount / `mknod` alias is NOT a workaround, and must never be
  added.** The image pipeline's `AGENTS.md` names it a corruption trap: aliasing
  the `system` heap hands MPP cached memory it will not synchronise, and aliasing
  the CMA heap caps out below 1080p (32 MiB pool, ~1.9 MiB largest run, ~3.1 MiB
  needed). It was a diagnostic instrument, never a fix.
- **The cacheable linear-map alias is deliberately left in place**, exactly as in
  the ACK heap this follows. That is the one thing a compile cannot vet: getting it
  subtly wrong yields silent intermittent video corruption, not an error. Hardware
  proof is therefore **mandatory, not advisable** — the legs are
  [`docs/BOARD-QUALIFICATION.md`](docs/BOARD-QUALIFICATION.md) §2-§7, and the
  reasoning is [`docs/UPSTREAM-STATUS.md` § `0009`](docs/UPSTREAM-STATUS.md#0009--why-hardware-proof-is-mandatory-here-and-not-merely-advisable).
- **It registers a name and nothing else.** Node mode and ownership stay the
  shipped `99-rk-device-permissions.rules` udev policy's job. Do not encode
  permissions in the kernel patch.

**`docs/BOARD-QUALIFICATION.md` is a specification, not a report — every item is
unchecked on purpose.** Producing the checklist and executing it are two different
jobs and only the first is done. Nothing in it has been run, so nothing in it may
be quoted as a result. It also deliberately carries `N/A` legs for the imports T12
and T13 evaluated and **declined** (I2S MCLK gating, PCIe system PM, V4L2 fdinfo
stats, tracepoints, SCDC debugfs): completeness there means the leg is *present and
marked*, not omitted, so a future reader can see it was considered. Do not delete
an `N/A` leg, do not tick one, and do not tick anything else without a pasted
transcript.

**The `78c67d98f221` HDMI-codec regression does NOT apply to this tree.** An
`armbian/linux-rockchip` commit zeroes `capture.channels_min/max` for every
`hdmi-audio-codec` instance with no TX/RX discrimination, which breaks HDMI-RX
capture on the **vendor** BSP (`rk-6.1-rkr6.1`). Mainline — including the pinned
`v7.1.7` — already carries the upstream `no_i2s_playback` / `no_i2s_capture` /
`no_spdif_*` pdata flags and only clears a direction when the registering driver
asks. There is nothing to fix here, and a backport of that vendor-side fix would
not even apply. Do not add one — the vendor-side fix lives in its own sibling
repo, [`CERALIVE/rk3588-vendor-kernel-patches`](https://github.com/CERALIVE/rk3588-vendor-kernel-patches),
pinned to `rk-6.1-rkr5.1` (the vendor branch the shipped image actually runs).
Send anyone who lands here looking for it there, and do not duplicate it here.

**The conflict rule is machine-enforced, not a convention.** A `rebase/*.rules`
entry may only re-anchor **context** lines. `build-series.py` raises if a rule's
anchor resolves to a `+`/`-` line or matches ambiguously, and
`verify-payload-parity.py` independently proves the ordered set of added/removed
lines in `patches/` is byte-identical to `upstream/`. If a conflict cannot be fixed
that way it is **behavioural**: STOP, write it up in `docs/REBASE-<tag>.md`, and
report the series as not applying. **Never invent a resolution** — this is
especially true for `0001`, ~4,200 lines of ported vendor driver code whose real
conflicts need someone who can test on RK3588 hardware.

**This repo pins a TAG; Armbian tracks a BRANCH.** Armbian's `edge` resolves to
`KERNELBRANCH="branch:linux-7.1.y"`, a rolling stable branch. This repo pins
`v7.1.7` = `c7ba9d6de43e9d9bd755b1f3c19501a38898c6b6`, the tip of that branch when
the pin was last taken. `apply.sh` refuses to run if the tag in the tree does not
resolve to the pinned commit *and* the pinned tag object, so a moved or re-created
tag fails loudly instead of going green against the wrong source. **Downstream
consumers must pin the same tag**, not follow `linux-7.1.y`.

**The `edge` mapping was verified fresh, and the family config is a trap.**
`config/sources/families/rockchip-rk3588.conf` handles only `legacy` and `vendor`
in its own `case $BRANCH` — reading it alone suggests `edge` is unsupported. In
fact it sources `rockchip64_common.inc` on line 10, and *that* file's `edge)` arm
sets `KERNEL_MAJOR_MINOR=7.1`. `preflight.sh` asserts the absence of an `edge)` case
in the family config precisely so a future Armbian change there cannot silently
invalidate the derivation.

**This does NOT change the shipped image's kernel.** The shipped image is locked to
the Armbian **vendor** BSP (`rk-6.1-rkr5.1`, `linux-image-vendor-rk35xx`) — image
pipeline Decision D3. That BSP has its own in-tree rkvenc/MPP stack and does not
need this series. This repo is the mainline-track option, kept applying and
audited; it is not a pending migration. Do not read its existence as reopening D3.

**Scope is patch application only.** No kernel is built, nothing is compiled, no
hardware is touched, and the DT overlay is carried verbatim without being compiled.
Kernel builds belong to `image-building-pipeline`.

**No MIT claim is made anywhere.** The new sources carry
`(GPL-2.0+ OR MIT)` + `MODULE_LICENSE("Dual MIT/GPL")`, and the Rockchip BSP
originals were verified to carry the same tags — so the dual grant is inherited,
not invented. But the upstream repo has **no `LICENSE` file**, and no line-by-line
derivation audit of the ported code was done. Only the GPL-2.0 branch is used.
Details and open questions: [`docs/PROVENANCE.md`](docs/PROVENANCE.md).

## PR TARGETING — READ THIS FIRST

**This repository is a GitHub fork, so `gh pr create` defaults its base to
`rcawston/rockchip-rk3588-mainline-patches`.** That is the exact failure mode the
root `AGENTS.md` records as having already sent a `srtla-send-rs` PR to
`irlserver/srtla_send`. Always be explicit:

```bash
gh pr create --repo CERALIVE/rk3588-kernel-patches --base main
gh pr view <n> --json url -q .url   # MUST be https://github.com/CERALIVE/...
```

Keep **only** `origin` (CERALIVE) attached at rest. If an upstream-sync ever needs
the parent, add it transiently as `rcawston` (**never** as `upstream`), fetch with
an explicit refspec, pin-verify the SHA, and remove it before any push or PR.

An upstream-sync PR that carries a real `git merge` commit must be **merge-commit
merged, never squashed** — squashing discards the second parent, so `git merge-base`
never advances and every later sync replays as phantom conflicts.

## CI

One workflow, `patch-apply.yml`, following the root CI/CD canon: `concurrency` with
`cancel-in-progress: true`; `push` constrained to `branches:` because a
`pull_request` trigger exists; top-level `permissions: contents: read`; actions
pinned to latest stable major; the ~2 GB kernel clone cached. Jobs:

| Job | Asserts |
|-----|---------|
| `series-integrity` | `patches/` is generated, payload-identical to its source lane (`upstream/`, `ceralive/` or `backports/`), and every lane file is accounted for exactly once; no Python needed beyond stdlib |
| `pin` | nothing — it *reads* `KERNEL_TAG` out of `kernel-pin.env` and emits the `apply` matrix |
| `preflight` | `kernel-pin.env` still matches `armbian/build` — non-blocking on schedule, blocking on PR |
| `apply` | `scripts/apply.sh` — the real `git am` against the pinned tag |

`apply` is the gate. It runs the same script the README tells humans to run, so a
broken instruction is a red build.

**No workflow restates a pinned coordinate.** The `apply` matrix used to be
`tag: [v7.1.5]`, which meant a `KERNEL_TAG` bump left CI proving the series against
a kernel nobody ships — and doing it *green*, which is the worst kind of failure.
The `pin` job now reads the tag from `kernel-pin.env` and the matrix is
`fromJSON(needs.pin.outputs.tags)`. There is no literal kernel tag anywhere in
`.github/`, and adding one back is a regression. `apply` still cross-checks its
matrix entry against `KERNEL_TAG`, because the cached commit it verifies against is
`KERNEL_COMMIT` and that is the commit of `KERNEL_TAG` and of nothing else.

There is **no build job**, deliberately. Adding one means a cross-compiler, a
defconfig, and a 30-minute job to prove something the image pipeline proves better.

## ANTI-PATTERNS

- Don't hand-edit `patches/` — regenerate from `upstream/` / `ceralive/` / `backports/` + `rebase/`
- Don't put CeraLive-authored or backported content in `upstream/`, or upstream content in the other lanes
- Don't make `verify-payload-parity.py` import from `build-series.py` — it is
  deliberately the second, independent opinion
- Don't `git rm` a source-lane patch — move it to `retired/` and register it
- Don't add a MERGED `backports/` patch without its own commit sha and lore Message-ID
- Don't put a commit sha, `NULL_OID`, a parent SHA or an `ALREADY upstream` claim on
  an UNMERGED lore-posting patch — it has no identity, and inventing one is false
  provenance, not a formatting shortcut
- Don't hand-transcribe a patch body when the canonical `t.mbox.gz` will not fetch —
  the candidate goes OUT `unfetchable-canonical-thread`
- Don't let a screened candidate leave no row in the reconciliation matrix; "not
  screened, and here is why" is a result, and an absent row reads as an oversight
- Don't add, import or retire a patch without updating its `docs/UPSTREAM-STATUS.md`
  row — including the **Last checked** date; a status change with a stale date is not a check
- Don't record a list-scoped lore URL, and don't re-capture the Collabora status
  table with `curl` — it is Anubis-gated and needs a real browser
- Don't rename, alias, symlink or `mknod` the `system-uncached` heap — the name is
  a userspace ABI and an alias is a corruption trap, not a workaround
- Don't tick anything in `docs/BOARD-QUALIFICATION.md` without a pasted transcript,
  and don't delete its `N/A` legs — a declined import that leaves no trace reads as
  a forgotten one
- Don't renumber the series to close the `0004` gap, or reuse a retired ordinal
- Don't restate a pinned coordinate in a workflow — read it from `kernel-pin.env`
- Don't strip quotes off a `kernel-pin.env` value by hand; `read_pin()` parses it
  the way bash does, inline `#` comments included
- Don't put a behavioural fix in `rebase/*.rules` — that is what the stop ledger is for
- Don't add a `+`/`-` line anywhere in this repo's patch pipeline; payload parity must hold
- Don't follow `linux-7.1.y` downstream — pin `KERNEL_TAG`
- Don't bump `KERNEL_TAG` without `scripts/preflight.sh --head` and a new `docs/REBASE-<tag>.md`
- Don't add this repo to `REPOS` or `versions.yaml` — it ships no artifact
- Don't let `gh pr create` pick the base branch (see PR TARGETING)
- Don't claim upstream-mergeable status, or assert the MIT branch of the licence
- Don't treat this repo's existence as reopening image-pipeline Decision D3
