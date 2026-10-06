# rk3588-kernel-patches

Parent: [workspace AGENTS.md](https://github.com/CERALIVE/ceralive/blob/master/AGENTS.md)

<!-- workspace-hard-rules:begin -->
## Workspace hard rules (identical in every CeraLive AGENTS.md)
- Commits and PRs carry the human author only: no Co-authored-by, no AI attribution.
- Start from the updated canonical branch; rebase to update; never `reset --hard` or discard others' work.
- One focused PR per repo, opened against CERALIVE/<repo>; the root policy PR merges first.
- A repo is self-contained: no path above its root; consume @ceralive packages from the registry, never link:/file:.
- Never delete, skip or weaken a test; every behavior change ships with a test.
- A user-visible change updates docs.ceralive.tv in English and Spanish (es-419), and any ceralive.tv claim it touches, in the same release.
- AGENTS.md holds rules and routing only, within budget; contracts and history live in docs/agents/.
- Full canon: https://github.com/CERALIVE/ceralive/blob/master/AGENTS.md
<!-- workspace-hard-rules:end -->

## ROLE

Mainline/edge RK3588 production patch series for the pinned 7.2 kernel.
Patch text only; image-building-pipeline builds the kernel. Vendor 6.1 is separate.

## STRUCTURE

```text
upstream/, ceralive/, backports/, island/ — source lanes
retired/ — byte-preserved archive and registry
patches/ — generated mailbox series
rebase/ — context-only rules
scripts/ — generator and independent gates
tests/ — tooling and helper fixtures
docs/ — ledgers, qualification and agent contracts
.github/ — patch-application CI
```

## COMMANDS

```sh
python3 scripts/build-series.py --check
python3 scripts/verify-payload-parity.py
python3 scripts/verify-island-provenance.py
python3 -m unittest discover -s tests
scripts/check-series-ledger.py --self-test
scripts/check-series-ledger.py --require-before U2:U1
scripts/check-series-ledger.py --exact docs/UPSTREAM-STATUS.md
tests/test_preflight_sovereign_pin.sh
scripts/preflight.sh
scripts/apply.sh
```

Read the [full CI contract](docs/agents/ci.md) and workflow for candidate-matrix coordinates and optional current Armbian reporting.

## WHERE TO LOOK

| Code path or task | Contract |
|---|---|
| Before changing anything else here, open docs/agents/README.md and read the contract for the subsystem you touch | [Contract index](docs/agents/README.md) |
| Overview | [overview.md](docs/agents/overview.md) |
| ROLE IN THE GROUP | [role-in-the-group.md](docs/agents/role-in-the-group.md) |
| STRUCTURE | [structure.md](docs/agents/structure.md) |
| WHERE TO LOOK | [where-to-look.md](docs/agents/where-to-look.md) |
| KEY FACTS | [key-facts.md](docs/agents/key-facts.md) |
| PR TARGETING — READ THIS FIRST | [pr-targeting-read-this-first.md](docs/agents/pr-targeting-read-this-first.md) |
| CI | [ci.md](docs/agents/ci.md) |
| ANTI-PATTERNS | [anti-patterns.md](docs/agents/anti-patterns.md) |

## HARD RULES

- Mainline/edge 7.2 only: VEPU580, HDMI-RX and first-party DT sound card; vendor 6.1 stays a separate repo, never cross-posted.
- Patch text only: no .deb, no image REPOS entry, no versions.yaml pin; no kernel build or hardware access here.
- Downstream patches_commit pins an immutable 40-character SHA; consumers pin the same kernel tag.
- kernel-pin.env owns every coordinate; workflows read it, never restate pins; verify commit AND annotated tag object.
- Never hand-edit patches/; regenerate from source lanes and context-only rebase rules.
- upstream/ stays byte-identical; never put first-party, backported or island content there.
- island/ assets stay byte-preserved with Island(tag, commit, asset_sha256) provenance; base conflicts need a new island release.
- Island and payload verifiers stay independent of build-series.py; regenerate headers and verify the release tuple.
- Merged backports require their own commit SHA and lore Message-ID; unmerged postings never claim any commit identity.
- Import unmerged postings only through import-lore-series.py and canonical t.mbox.gz; unfetchable means OUT, never hand-transcribe.
- Retire source patches byte-unchanged into retired/ with a registry row; never delete, reuse ordinals or close the 0004 gap.
- Each lane file is active or retired exactly once; SERIES_TOTAL is the slot ceiling, not the member count.
- Patch add/import/retirement updates UPSTREAM-STATUS.md and Last checked; every screened candidate needs a matrix row.
- rebase rules never touch +/- lines; first-party revisions need intent ledgers; other payload drift needs a fresh fixup or STOP.
- system-uncached is a userspace ABI: never rename or alias it; permissions stay in udev; hardware proof is mandatory.
- Never restore ASoC callbacks/control mutex use in the audio worker; preserve RK3588 HDMI-IN and both boards' DT wiring.
- Never claim 0050 fixes RGA2 SError or invent its Fixes tag; quote board results only with matching pasted transcripts/base.
- Keep N/A board legs; never tick unrun work or claim mock/code evidence as hardware qualification or the MIT licence branch.
- Kernel bumps need preflight --head and a new REBASE ledger; Armbian mapping is informational, never sovereign pin authority.
- PRs explicitly target CERALIVE/main; only origin at rest; upstream-sync merges retain both parents, never squash.
