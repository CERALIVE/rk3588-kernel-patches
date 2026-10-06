<!-- Moved verbatim from AGENTS.md on 2026-10-05 by lean-rules-docs-landing-latam -->

## STRUCTURE

```
rk3588-kernel-patches/
├── kernel-pin.env             # SINGLE SOURCE OF TRUTH for every pinned coordinate
├── upstream/                  # SOURCE LANE — Ross Cawston's raw diff -ruN files, VERBATIM + README.MD
├── ceralive/                  # SOURCE LANE — FIRST-PARTY raw diffs with no upstream counterpart
├── backports/                 # SOURCE LANE — externally-sourced patches, each carrying its OWN provenance
│   └── lore/<alias>/          # canonical mail of each UNMERGED posting, so its digest is recomputable offline
├── island/                    # SOURCE LANE — byte-preserved rk3588-media-island release mailboxes
├── retired/                   # ARCHIVE — patches moved out of the series, byte-unchanged
│   └── REGISTRY.md            # the RETIRED registry: state machine + the retirement table
├── patches/                   # GENERATED git-am series + series file — NEVER hand-edit
├── rebase/<tag>.rules         # per-kernel-tag context re-anchors (context lines ONLY)
├── scripts/
│   ├── preflight.sh           # validate the sovereign pin; optionally report Armbian mapping
│   ├── build-series.py        # source lanes -> patches/ ; --check asserts in-sync; orphan check
│   ├── verify-payload-parity.py  # proves patches/ changes nothing its source lane didn't
│   ├── verify-island-provenance.py # release SHA-256 + byte comparison; independent of generator
│   ├── import-lore-series.py  # the ONLY sanctioned way to import an unmerged posting
│   ├── validate-candidate-matrix.py  # every screened candidate has every field
│   ├── check-series-ledger.py # SERIES <-> patches/ <-> UPSTREAM-STATUS.md, compared exactly
│   └── apply.sh               # the gate: verify -> clone pinned tag -> git am -> assert
├── tests/                     # stdlib unittest fixtures for the Python tooling
├── docs/
│   ├── UPSTREAM-STATUS.md     # per-patch upstream status + retire-on-merge triggers
│   ├── BOARD-QUALIFICATION.md # the hardware checklist + its Run log — runs 1 and 2 executed
│   ├── EVAL-0002-EDID.md      # verdict: keep 0002; the 7.2-rc1 fix is already in the base
│   ├── EVAL-0005-AUDIO.md     # historical KEEP verdict; superseded by the v4 reconciliation ledger
│   ├── AUDIO-V4-VALIDATION.md # what the v4 migration gate ran, and what it does not claim
│   ├── EDID-STREAMING-GUARD.md # deferred board procedure for 0040
│   ├── PROVENANCE.md          # licence/provenance audit incl. the MIT-claim caveat
│   ├── PREFLIGHT.md           # how the Armbian bleedingedge -> 7.2 mapping was derived
│   ├── REBASE-v7.2.md         # hunk-by-hunk rebase ledger — CURRENT base; a verdict per ordinal, 0009 + 0018 revised, 0007 retired
│   ├── REBASE-v7.1.7.md       # ledger for the previous base, kept for the record
│   └── REBASE-v7.1.5.md       # ledger for the base before that, likewise
└── .github/workflows/patch-apply.yml
```

