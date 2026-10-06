<!-- Moved verbatim from AGENTS.md on 2026-10-05 by lean-rules-docs-landing-latam -->

## ANTI-PATTERNS

- Don't hand-edit `patches/` — regenerate from `upstream/` / `ceralive/` / `backports/` / `island/` + `rebase/`
- Don't hand-edit or re-anchor `island/`; import release-asset members byte-preserved and verify them independently
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
  as a member count — it is 50 slots holding 32 members
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
- Don't describe the retired vendor 6.1 track as production; mainline 7.2 is permanent
