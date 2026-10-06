<!-- Moved verbatim from AGENTS.md on 2026-10-05 by lean-rules-docs-landing-latam -->

## CI

One workflow, `patch-apply.yml`, following the root CI/CD canon: `concurrency` with
`cancel-in-progress: true`; `push` constrained to `branches:` because a
`pull_request` trigger exists; top-level `permissions: contents: read`; actions
pinned to latest stable major; the ~2 GB kernel clone cached. Jobs:

| Job | Asserts |
|-----|---------|
| `series-integrity` | `patches/` is generated, payload-identical to its source lane, island members match the release asset, and every lane file is accounted for exactly once; no Python needed beyond stdlib |
| `pin` | nothing — it *reads* `KERNEL_TAG` out of `kernel-pin.env` and emits the `apply` matrix |
| `preflight` | CeraLive's own pin is valid; Armbian mapping is informational only |
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

