# Retired patch registry

This directory is the **archive**, and the table at the bottom is the **registry**.
Together they are the only legal way for a patch to leave the series.

`scripts/build-series.py` parses this file. It is documentation and machine input
at once, deliberately — the same choice `rebase/*.rules` makes — so there is no
second copy of the state to drift out of sync.

---

## Why deletion is not an option

`upstream/` has to stay byte-identical to what Ross Cawston published, forever.
That is the sentence the credit line, the licence audit in
[`docs/PROVENANCE.md`](../docs/PROVENANCE.md) and the parity claim in
[`README.md`](../README.md) all rest on, and it is only checkable while the files
are still here to check.

`git rm` would make it unfalsifiable. A reviewer looking at a four-file `upstream/`
cannot tell "upstream only ever published four" from "someone quietly dropped the
fifth" without walking history. So a patch that stops being carried is **moved**,
not removed, and the move is recorded below.

The same reasoning covers the other two lanes for a different reason: a retired
`ceralive/` or `backports/` patch is the record of something CeraLive once shipped
or once needed, and the registry row is where the *why* lives.

---

## The state machine

Every `*.patch` under `upstream/`, `ceralive/` or `backports/` — plus every
`*.patch` under `retired/` — is in exactly one of two states, and
`check_membership()` in `scripts/build-series.py` fails the build if it is in both
or neither.

```
              new file in upstream/ | ceralive/ | backports/
                              │
                              │  add a SERIES entry in scripts/build-series.py
                              ▼
   ┌────────────────────► ACTIVE ◄────────────────────┐
   │                 <lane>/<file>.patch              │
   │                 + SERIES entry                   │
   │                 + patches/<file>.patch           │
   │                                                  │
   │  RETIRE                                REINSTATE │
   │   1. git mv <lane>/<f> retired/<f>      1. git mv retired/<f> <lane>/<f>
   │      (byte-unchanged — never re-emit)   2. re-add the SERIES entry with
   │   2. delete the SERIES entry               its ORIGINAL ordinal
   │   3. add a row to the table below       3. delete its row below
   │   4. scripts/build-series.py            4. scripts/build-series.py
   │                                                  │
   └────────────────────► RETIRED ◄───────────────────┘
                     retired/<file>.patch
                     + one row in this table
                     + NO SERIES entry
```

**Invariants the build enforces**

- A source-lane file with no `SERIES` entry and no row here is an **orphan** —
  the build fails rather than silently ignoring it.
- A row here with no file in `retired/` is a **deletion** — the build fails.
- A file in `retired/` with no row here is an **unexplained archive** — the build
  fails.
- A file that is both active and retired fails.
- A retired ordinal is **never reused**. The `0004` gap already proves this repo
  keeps holes visible; a retirement just adds another one. `SERIES_TOTAL` is a
  slot count, so it does not shrink when a patch retires.
- Retiring changes `patches/` only by regeneration. The archived file itself is
  never rewritten, so its payload stays comparable to what was imported.

**Retiring is not the same as rebasing.** If a patch merely stops *applying*, that
is a conflict: it belongs in `docs/REBASE-<tag>.md`, or in a context-only
`rebase/<tag>.rules` entry. Retire a patch when it stops being *wanted* — landed
upstream, superseded, or scoped out.

---

## Registry

| Patch | Lane | Ordinal | Retired | Kernel tag | Reason |
|-------|------|---------|---------|------------|--------|
| `0007-iommu-rockchip-disable-fetch-dte-time-limit.patch` | `backports` | 7 | 2026-08-26 | `v7.2` | Landed upstream — 8d4346ecd495 in v7.2 |
| `0023-rkvenc-worker-task-lifetime.patch` | `ceralive` | 23 | 2026-08-12 | `v7.1.7` | Folded into `0021` — the worker use-after-free half. See `docs/UPSTREAM-STATUS.md` § retired ordinals |
| `0024-rkvenc-secondary-core-iommu-domain-lifetime.patch` | `ceralive` | 24 | 2026-08-12 | `v7.1.7` | Folded into `0021` — the secondary-core NULL-domain half. See `docs/UPSTREAM-STATUS.md` § retired ordinals |
| `0025-rkvenc-service-node-teardown-lifetime.patch` | `ceralive` | 25 | 2026-08-12 | `v7.1.7` | Folded into `0021` — the service-node teardown half. See `docs/UPSTREAM-STATUS.md` § retired ordinals |

**Folded, not dropped.** These three are the only rows here that retire a patch
whose *content the series still carries*: `0021`, `0023`, `0024` and `0025` fixed
four defects in one rkvenc task/core/service lifecycle, found one at a time on a
real Rock 5B+ because each fix made the next reachable, and they were merged into
`0021` so a reader who hits any one symptom gets all four. The fold was proven
byte-neutral before it landed: `0001`-`0020` + the merged `0021` + `0022` + `0026`
produces git tree `e8133646d100f528c17f1834a82f20becfc48b6a`, the same tree object
the four-patch sequence produced. The archived files below are the record of what
each ordinal individually documented, and their ordinals are burned like `0004`'s.

Column meanings:

| Column | Content |
|--------|---------|
| `Patch` | The archived filename, exactly as it appears in `retired/` |
| `Lane` | The lane it was moved out of: `upstream`, `ceralive` or `backports` |
| `Ordinal` | The series slot it held. Permanently burned; never reused |
| `Retired` | ISO date of the retirement commit |
| `Kernel tag` | `KERNEL_TAG` at the time, so the row is anchored to a tree |
| `Reason` | One line. Landed upstream / superseded by NNNN / scoped out — and where the detail lives |
