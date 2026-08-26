# rk3588-kernel-patches

## ROLE IN THE GROUP

Holds the **mainline-track RK3588 kernel patch series** for CeraLive: VEPU580
hardware encoder plus three HDMI-RX fixes imported from upstream, three
backported **unmerged lore postings** (a combphy erratum and two dw-hdmi-qp audio
fixes), and first-party patches for HDMI-RX audio DT, encoder DMA/dma-heap fixes,
and rkvenc/HDMI-RX quality hardening (including the 4K60 SCDC bit-clock-ratio
recovery, `0027`) — converted to a `git am` mailbox series and pinned to an exact
kernel tag.

The base is **`v7.2`**; the series is re-anchored onto it and applies clean. **22
members are active across 27 slots** — `0004` was never published, and `0007`,
`0023`, `0024` and `0025` are retired ordinals whose slots stay burned. Board
evidence quoted anywhere in this repo was measured at the previous `v7.1.7` base
and is historical here.

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
│   ├── BOARD-QUALIFICATION.md # the hardware checklist + its Run log — runs 1 and 2 executed
│   ├── EVAL-0002-EDID.md      # verdict: keep 0002; the 7.2-rc1 fix is already in the base
│   ├── EVAL-0005-AUDIO.md     # verdict: keep 0005+0006; the lore v4 series drops Rock 5B+
│   ├── PROVENANCE.md          # licence/provenance audit incl. the MIT-claim caveat
│   ├── PREFLIGHT.md           # how the Armbian bleedingedge -> 7.2 mapping was derived
│   ├── REBASE-v7.2.md         # hunk-by-hunk rebase ledger — CURRENT base; a verdict per ordinal, 0009 + 0018 revised, 0007 retired
│   ├── REBASE-v7.1.7.md       # ledger for the previous base, kept for the record
│   └── REBASE-v7.1.5.md       # ledger for the base before that, likewise
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
| Understand the `bleedingedge` → 7.2 derivation | [`docs/PREFLIGHT.md`](docs/PREFLIGHT.md) |
| Apply the series | `scripts/apply.sh` — see [`README.md`](README.md) |
| Why a hunk was re-anchored, or a member revised, at the current base | [`docs/REBASE-v7.2.md`](docs/REBASE-v7.2.md) |
| What an earlier base needed | [`docs/REBASE-v7.1.7.md`](docs/REBASE-v7.1.7.md), [`docs/REBASE-v7.1.5.md`](docs/REBASE-v7.1.5.md) |
| Why an ordinal is retired, and where its file went | [`retired/REGISTRY.md`](retired/REGISTRY.md) + [`docs/UPSTREAM-STATUS.md` § retired ordinals](docs/UPSTREAM-STATUS.md#retired-ordinals-0007-0023-0024-0025) |
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
`upstream/` lane hard-codes a single credit block true of every file in that
directory and of nothing else, so every `backports/` member must name its own
origin: `provenance` is the 40-hex commit it is backported from (never
`NULL_OID`, which is 40 hex digits and would otherwise pass the shape test),
and `Backport(upstream_subject=…, lore_msgid=…, note=…)` supplies the rest. The
generated header emits `commit <sha> upstream.` plus a lore link. The build
refuses an entry lacking any of it. Details: [`backports/README.md`](backports/README.md).

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
record list-scoped URLs. Its Collabora source table is re-captured through the
GitLab **REST API** route, which was **ungated when last checked (2026-08-26)** —
plain `curl` got the file with no challenge. The gate has been up before and can
return, so the real-browser fallback stays documented rather than deleted; check
which one you are getting before concluding anything from a short response.

**`0002` has exactly ONE upstream answer, we already ship it, and it is not a
replacement.** `7dd27810eea0` ("hdmirx: Fix HPD lane hold time", in the base since
`v7.1.6`) **is** the 7.2-rc1 "HDMI-RX EDID fix" — the stable backport of mainline
`d1162a5adbb5`. The table names the symptom, the patch names the mechanism; it
applied to `v7.1.7` as a **no-op**, it is in the `v7.2` base as mainline, and it
shares no mechanism with `0002`'s IRQ masking, lock-loop rework and DMA reset — so
there is nothing to adopt and nothing to retire. `0002`'s own three symbols are
still absent from the base. Whether `0002` is still *needed* on top of it is a
behavioural judgement needing an RK3588 board and an HDMI source — do not
resolve that from source alone. Verdict: [`docs/EVAL-0002-EDID.md`](docs/EVAL-0002-EDID.md); see also
[`docs/UPSTREAM-STATUS.md`](docs/UPSTREAM-STATUS.md) § `0002` and
[`docs/REBASE-v7.1.7.md`](docs/REBASE-v7.1.7.md) § Stable overlap.

**Resolving a lore Message-ID does not need a browser — but try both routes, and
never spoof a browser User-Agent.** `lore.kernel.org`'s HTML views and its `/raw`
endpoint are Anubis-gated (`curl` gets 403 or a proof-of-work page). Anubis keys
on the **UA**, and it does so in the direction that surprises people: sending
`Mozilla/5.0` to the canonical `t.mbox.gz` returns **HTTP 200 wrapping a challenge
page**, so a status-code-only check reads as success and yields no mbox, while
`curl`'s own default UA gets the real gzip. Two ways through, and neither covers
every posting on its own:

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

The Collabora **table** is a third case and neither of these routes reaches it. It
is re-captured through the GitLab REST API, ungated as of 2026-08-26 — see the
retire-trigger fact above for the caveat.

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
backported patches continue the same counter (`0006`, `0008`, `0009` and
`0013`–`0022`, `0026` and `0027` = `ceralive/`; `0010`, `0011` and `0012` =
`backports/`), so the ordinals read `1/27`, `2/27`, `3/27`, `5/27` … `27/27` — the
gap at 4 stays visible, which is the whole point. **`0007`, `0023`, `0024` and
`0025` are four more gaps**, retired rather than never-published: `0007` because
the `v7.2` base absorbed the mainline commit it backported, and the other three
because they were folded into `0021`. All four slots are burned, exactly like
`0004`'s. That leaves **22 active members across 27 slots**, and the two numbers
are not interchangeable: `SERIES_TOTAL` in `build-series.py` is the **slot** count
including every gap, not the member count, and the build refuses an ordinal above
it because the `N/SERIES_TOTAL` subject would otherwise lie. A retirement does not
shrink it.

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
pairing.** A real, fully-reviewed lore series
(<https://lore.kernel.org/r/20260721064115.64809-1-royalnet026@gmail.com>,
`[PATCH v4 0/4]`, Igor Paunovic) does what `0005` does and carries its own DT
patches, but its 4/4 enables the card on Orange Pi 5 Plus **only** — Rock 5B+
gets nothing, the exact bound-codec-no-card state above. The two DT halves also
disagree on cell arity (`#sound-dai-cells = <0>` vs `<1>`) and cannot coexist.
Adoptable mechanically — all four patches apply clean — but declined: it also
drops multichannel handling, jack reporting and `hdmirx_plugout()` teardown.
Full six-criteria verdict: [`docs/EVAL-0005-AUDIO.md`](docs/EVAL-0005-AUDIO.md).
Re-open only when the series is *merged* and Rock 5B+ is covered.

**`0008` fixes `0001`, is marked `UNVALIDATED`, and does NOT alone make the
edge-track encoder work.** `rkvenc_dma_import_fd()` recorded an imported dma-buf's
length from the FIRST mapped segment only, and `0001` never set a max segment
size, so every import over 64 KiB was recorded as exactly `0x10000` bytes.
`0008` sets the cap in `rkvenc_hw_probe()` and **reads it back**, failing the
probe with `-EINVAL` if it did not take — `dma_set_max_seg_size()` returns
`void` at the pinned base, so checking the effect is the only check available.

Two things about it are easy to get wrong:

- **The IOVA guardrail in `rkvenc_service.c` is deliberately NOT touched, and must
  stay that way.** With the window truncated to 64 KiB, an NV12 chroma-plane
  offset really is outside `[iova, iova+len)`, so the guardrail was correct every
  time it fired. Silencing it trades a clean `-EINVAL` for a DMA write past the
  end of a mapping. `0008` touches exactly one file (`rkvenc_hw.c`).
- **This is one of THREE stacked defects.** The other two — `librockchip-mpp`
  hard-coding a `system-uncached` dma-heap mainline does not register, and
  mainline having no uncached heap to fall back to — are answered in source by
  `0009`, also **`UNVALIDATED`**. Do not describe MPP hardware encode as fixed
  on the `edge` track until both are cleared together. Full three-defect
  analysis: the `image-building-pipeline` `AGENTS.md` KNOWN ISSUE "MPP hardware
  video encode does not work on the edge kernel". Marker and clearing
  conditions: [`docs/UPSTREAM-STATUS.md` § `0008`](docs/UPSTREAM-STATUS.md#0008--unvalidated-and-what-that-does-and-does-not-mean).

**`0013`–`0022`, `0026` and `0027` are the first-party rkvenc / HDMI-RX / dma-heap
quality block, and the ones a board has actually run are the exception.** `0013` is
gated fault injection that contributes zero bytes to a production build; `0018`
states an existing API's failure semantics truthfully rather than fixing a defect;
`0014`–`0017` repair concrete defects in the code that runs when something goes
wrong. `0019`–`0022`, `0026` and `0027` are different in kind: each was root-caused
from a **real Rock 5B+ transcript**, not from reading — and `0027` and `0022`'s
current version went further, landing with their *fix* proven on the board rather
than only their defect.
Per-patch detail — what each fixes,
what it deliberately does not, and what would retire it — lives in
[`docs/UPSTREAM-STATUS.md`](docs/UPSTREAM-STATUS.md), one row each; do not restate
it here.

Three things about this block are easy to get wrong:

- **"Marked done" and "verified" are different claims, and this block is the
  proof.** `0015` and `0016` were both landed and ticked before anything ran on
  hardware. The first real drill against them failed: `0021` fixes the rkvenc
  task/core/service lifecycle `0015` made *reachable* (it propagated a clock-enable
  failure that used to be discarded; the unconditional release is `0001`'s), and
  `0022` fixes three of four still-failing cases in `tests/expected-errno.tsv`
  that `0016` was supposed to have closed. Do not read a landed patch as a
  validated one — read its `UNVALIDATED` marker.
- **`0022` is the sharpest instance of that, because it was broken by hardware
  TWICE.** v1 passed every fault case written for it and refused every production
  encode. v2 fixed that, passed a cold-boot control encode, and shipped a **total
  H.265 outage** — MPP's HEVC programme is one write spanning `SQI` and `SCL`
  across a genuine 24-byte map hole, and v2's rule was "one contiguous run". The
  control encode that caught v1 ran H.264 only, so it could not catch v2. The
  standing gate is therefore a cold-boot, no-fault control encode **per codec the
  board can be asked for**, not one encode. Detail:
  [`docs/UPSTREAM-STATUS.md` § `0022`](docs/UPSTREAM-STATUS.md#0022--what-it-fixes-what-it-does-not-and-the-one-case-still-red).
- **`0021` is ONE patch covering FOUR defects, and that is deliberate.** It was
  carried as `0021`+`0023`+`0024`+`0025` while the defects were being discovered on
  a board — balance, then worker lifetime, then core lifetime, then service
  lifetime, each fix making the next reachable — and folded once the picture was
  whole, because three of the four are unreachable in isolation. The fold was
  proven **byte-neutral** (identical `git am` tree object) before it landed, so
  every hardware result recorded against the old ordinals still stands. Do not
  re-split it, and do not treat a `git blame` hit on `0023`/`0024`/`0025` as a
  missing patch: [`docs/UPSTREAM-STATUS.md` § retired ordinals](docs/UPSTREAM-STATUS.md#retired-ordinals-0007-0023-0024-0025)
  is the map. One comment in `rkvenc_drv.c` still names `0024`; that is correct
  history, and rewording it would have broken the byte-neutrality proof.
- **A green `rkvenc-invalid-ioctl --all-malformed` is NOT the acceptance criterion
  for `0022`.** One case, `valid-after-failures`, is expected to stay red for a
  reason that is the harness's and not the driver's, and two of `0022`'s bounds
  fixes have no drill case at all. Both are written up in
  [`docs/UPSTREAM-STATUS.md` § `0022`](docs/UPSTREAM-STATUS.md#0022--what-it-fixes-what-it-does-not-and-the-one-case-still-red).
  Do not "fix" the red case by editing the expectation table.

**`0009` is defects 1+3 of the same three, is `UNVALIDATED`, and its NAME is a
userspace ABI.** `librockchip-mpp` hard-codes the `system-uncached` dma-heap
name, which mainline does not register — so `mpph264enc` never registered at
all (defect 1) — and MPP performs no CPU cache maintenance on a heap it
believes is uncached, so cached memory under that name produced non-deterministic
output (defect 3). `0009` registers a second heap out of `system_heap.c`'s
existing per-heap drvdata mechanism: non-cacheable mappings, a one-time
`arch_dma_prep_coherent()` clean at allocation, and skipped CPU-sync **only**
for that heap.

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

**`docs/BOARD-QUALIFICATION.md` was written as a specification and is now also a
report — read its Run log before quoting anything from it.** Producing the checklist
and executing it are two different jobs, and the second one has now been done twice:
run 1 (2026-08-09, Rock 5B+) ticked §2–§7 and §10a, and run 2 (2026-08-10 → 08-12,
both boards) added the fault-injection campaign behind `0021`, `0022` and `0026`. An
item is quotable as a result **only** where a `RUN-n` note is pasted under it; an
unticked box still means not run, not "assumed fine". It also carries `N/A` legs for the imports T12
and T13 evaluated and **declined** (I2S MCLK gating, PCIe system PM, V4L2 fdinfo
stats, tracepoints, SCDC debugfs): completeness there means the leg is *present and
marked*, not omitted, so a future reader can see it was considered. Do not delete
an `N/A` leg, do not tick one, and do not tick anything else without a pasted
transcript.

**The `78c67d98f221` HDMI-codec regression does NOT apply to this tree.** An
`armbian/linux-rockchip` commit zeroes `capture.channels_min/max` for every
`hdmi-audio-codec` instance with no TX/RX discrimination, which breaks HDMI-RX
capture on the **vendor** BSP (`rk-6.1-rkr6.1`). Mainline — including the pinned
`v7.2` — already carries the upstream `no_i2s_playback` / `no_i2s_capture` /
`no_spdif_*` pdata flags and only clears a direction when the registering driver
asks. There is nothing to fix here, and a backport of that vendor-side fix would
not even apply. Do not add one — the vendor-side fix lives in its own sibling
repo, [`CERALIVE/rk3588-vendor-kernel-patches`](https://github.com/CERALIVE/rk3588-vendor-kernel-patches),
pinned to `rk-6.1-rkr5.1` (the vendor branch the shipped image actually runs).
Send anyone who lands here looking for it there, and do not duplicate it here.

`rebase/*.rules` are context-only for ALL lanes. At a base bump, `ceralive/`-lane patches MAY be revised in place (payload changes) to preserve their documented intent on the new base; every such revision is recorded hunk-by-hunk in `docs/REBASE-<tag>.md` with an intent-preservation note, and is verified by the post-apply assertions and the bump's compile evidence. Payload drift in `upstream/` or `backports/` lanes remains behavioural: resolve ONLY by a new `ceralive/` fixup patch at a fresh ordinal (the 0008-fixes-0001 pattern) or STOP and report. `upstream/` bytes are never edited.

**This repo pins a FINAL TAG; Armbian's `bleedingedge` arm still names a release
candidate.** The branch this repo derives its mapping from is `bleedingedge`, and
`config/sources/mainline-kernel.conf.sh` pins it to `tag:v7.2-rc7` because
Armbian's roll-over-once-7.2-ships TODO has not been actioned. `v7.2` final was
tagged one day *before* the recorded framework revision, so the rc is simply
stale, and gating this series on a kernel nobody will run would be the wrong
trade. This repo therefore pins `v7.2` = `8d3ae59288f1e7d58d76558a6ee96d533bc5019f`,
tag object `237a1c39e8dfd3e1c6f1f023eea37a48ec04cc63`. The `MAJOR.MINOR` — and so
the config and patch-directory names — is identical either way, which is what
makes the substitution safe. `apply.sh` refuses to run if the tag in the tree does
not resolve to the pinned commit *and* the pinned tag object, so a moved or
re-created tag fails loudly instead of going green against the wrong source.
**Downstream consumers must pin the same tag.**

**The `bleedingedge` mapping was verified fresh, and the family config is a trap.**
`config/sources/families/rockchip-rk3588.conf` handles only `legacy` and `vendor`
in its own `case $BRANCH`, which alone suggests `bleedingedge` is unsupported — but
it sources `rockchip64_common.inc`, whose `bleedingedge)` arm sets
`KERNEL_MAJOR_MINOR=7.2`. `preflight.sh` asserts the absence of a
`bleedingedge)` case in the family config so a future Armbian change there cannot
silently invalidate the derivation, and it asserts Armbian's explicit `7.2` arm and
its keyed source override too. The same trap caught the previous `edge` → `7.1`
derivation; the shape of the mistake outlived the branch name.

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
`tag: [v7.1.5]`, which meant a `KERNEL_TAG` bump left CI proving the series
against a kernel nobody ships — green, the worst kind of failure. The `pin` job
now reads the tag from `kernel-pin.env` (`fromJSON(needs.pin.outputs.tags)`); no
literal kernel tag exists anywhere in `.github/`, and adding one back is a
regression. `apply` still cross-checks its matrix entry against `KERNEL_TAG`.

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
- Don't record a list-scoped lore URL, and don't spoof a browser User-Agent on a
  lore fetch — Anubis answers `Mozilla/5.0` with an HTTP 200 challenge page, so
  the spoof is what breaks it, not what gets you through
- Don't renumber to close a retired ordinal's slot, and don't read `SERIES_TOTAL`
  as a member count — it is 27 slots holding 22 members
- Don't rename, alias, symlink or `mknod` the `system-uncached` heap — the name is
  a userspace ABI and an alias is a corruption trap, not a workaround
- Don't tick anything in `docs/BOARD-QUALIFICATION.md` without a pasted transcript,
  and don't delete its `N/A` legs — a declined import that leaves no trace reads as
  a forgotten one
- Don't renumber the series to close the `0004` gap, or reuse a retired ordinal
- Don't restate a pinned coordinate in a workflow — read it from `kernel-pin.env`
- Don't strip quotes off a `kernel-pin.env` value by hand; `read_pin()` parses it
  the way bash does, inline `#` comments included
- Don't put a behavioural fix in `rebase/*.rules`; revise a `ceralive/` source patch in place with a hunk-by-hunk intent-preservation note, add a fresh-ordinal `ceralive/` fixup for `upstream/` or `backports/` drift, or STOP and report
- Don't let a `rebase/*.rules` entry touch a `+`/`-` line; rules are context-only for every lane
- Don't follow Armbian's branch downstream, and don't pin its release candidate — pin `KERNEL_TAG`
- Don't bump `KERNEL_TAG` without `scripts/preflight.sh --head` and a new `docs/REBASE-<tag>.md`
- Don't add this repo to `REPOS` or `versions.yaml` — it ships no artifact
- Don't let `gh pr create` pick the base branch (see PR TARGETING)
- Don't claim upstream-mergeable status, or assert the MIT branch of the licence
- Don't treat this repo's existence as reopening image-pipeline Decision D3
