# Preflight — how the Armbian rk3588 `bleedingedge` kernel was resolved

Everything in [`kernel-pin.env`](../kernel-pin.env) was **read out of Armbian's
own configuration at a recorded revision**, not copied from a wiki or from a
previous investigation. This page shows the derivation so it can be re-checked.

Re-run it yourself at any time:

```bash
scripts/preflight.sh          # against the pinned ARMBIAN_BUILD_REV
scripts/preflight.sh --head   # against armbian/build's current main
```

The `--head` form is the one that answers *"has Armbian moved `bleedingedge`
since this was pinned?"*, and it is what CI runs on a schedule.

---

## What Armbian is consulted for — and what it is not

This is the single most misread thing on this page, so it goes first.

Armbian is read here **as a mapping observation**: it answers *"which mainline
MAJOR.MINOR does the rk3588 family associate with a branch name, and under which
config and patch-directory names"*. That is what makes `rockchip64-7.2` a derived
fact instead of a guess.

Armbian is **not** read as a build instruction. CeraLive does not invoke
`compile.sh`; the kernel is built from source by `image-building-pipeline`
against `KERNEL_TAG`. Two consequences follow, and both are deliberate:

- **`KERNEL_TARGET` does not gate anything.** Neither board lists
  `bleedingedge` in its branch menu (below). That is a statement about which
  branches Armbian's *own menu* offers, not about which kernel the source can be
  built against. `preflight.sh` prints both values and never fails on them —
  making that an assertion would gate a real pin on an unrelated Armbian UI
  decision.
- **We pin the final release where Armbian pins a release candidate.** See
  [Why the pin is `v7.2` and not `v7.2-rc7`](#why-the-pin-is-v72-and-not-v72-rc7).

---

## Resolved on 2026-08-26

**Framework revision:** `armbian/build` `main` @ `8af7de8d4117d058e3cda0907f08325aa809da9e`
(committed 2026-08-17).

> The previous pin was `edge` → `7.1` at framework revision
> `587b6f2c0a867859ca3f323f6008bee9e3ef1553` (2026-07-31). Both the branch and
> the framework revision moved here; nothing was carried over unverified.

### Boards

Both CeraLive RK3588 targets resolve to the same Armbian family, so one mapping
covers both.

| Armbian board config | `BOARDFAMILY` | `KERNEL_TARGET` |
|---|---|---|
| `config/boards/rock-5b-plus.conf` | `rockchip-rk3588` | `vendor,current,edge` |
| `config/boards/orangepi5-plus.conf` | `rockchip-rk3588` | `current,edge,vendor` |

**Neither lists `bleedingedge`, and that is fine** — see the section above. The
`BOARDFAMILY` value *is* gating, because the whole derivation below hangs off it.

### The derivation chain (four files, in order)

**1. `config/sources/families/rockchip-rk3588.conf`**

Line 10 sources the common include *before* anything else:

```bash
source "${BASH_SOURCE%/*}/include/rockchip64_common.inc"
```

Its own `case $BRANCH` then handles **only `legacy` and `vendor`**. There is no
`bleedingedge)` arm. This is the step that is easy to get wrong: reading this
file alone suggests the branch is unsupported, when in fact it simply keeps
whatever the include already set. `scripts/preflight.sh` asserts the absence of a
`bleedingedge)` case so that a future Armbian change here cannot silently
invalidate the chain. (The `edge` derivation this replaced had the identical
trap.)

**2. `config/sources/families/include/rockchip64_common.inc`**

```bash
bleedingedge)
    declare -g KERNEL_MAJOR_MINOR="7.2"
    declare -g LINUXFAMILY=rockchip64
    declare -g LINUXCONFIG='linux-rockchip64-'$BRANCH
    ;;
```

For context, the neighbouring arms are `current` → `6.18` and `edge` → `7.1`.

`LINUXCONFIG` is an **interpolation, not a literal** — the branch name is spliced
in, so it resolves to `linux-rockchip64-bleedingedge` and hence
`config/kernel/linux-rockchip64-bleedingedge.config`. `preflight.sh` expands
`$BRANCH` the way Armbian would rather than string-matching the raw line, then
separately confirms that config file actually **exists** at the pinned revision —
a derived name that names no file would otherwise be a silent failure downstream.

**3. `config/sources/mainline-kernel.conf.sh` — the branch**

Unlike `7.1`, this version has an **explicit** arm, so the rolling stable default
never runs:

```bash
function mainline_kernel_decide_version__upstream_release_candidate_number() {
    [[ -n "${KERNELBRANCH}" ]] && return 0
    if [[ "${KERNEL_MAJOR_MINOR}" == "7.2" ]]; then   # @TODO: roll over ... when it is released
        declare -g KERNELBRANCH="tag:v7.2-rc7"
    fi
}
```

→ `tag:v7.2-rc7`.

Every hook in this chain returns early if `KERNELBRANCH` is already set, so an
explicit arm makes `__900_defaults`' `branch:linux-${KERNEL_MAJOR_MINOR}.y`
unreachable for that version.

**4. `config/sources/mainline-kernel.conf.sh` — the source**

A later hook then redirects `KERNELSOURCE`, keyed on the branch value the hook
above just set:

```bash
function mainline_kernel_decide_version__750_use_torvalds_for_7.2-rc7() {
    if [[ "${KERNELBRANCH}" == 'tag:v7.2-rc7' ]]; then
        declare -g KERNELSOURCE="https://github.com/torvalds/linux.git"
    fi
}
```

→ `https://github.com/torvalds/linux.git`, in place of the mainline default
(`https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git`, from
`lib/functions/configuration/main-config.sh`).

That redirect is an emergency hook for a tag kernel.org had not yet mirrored, and
it **no longer describes reality** — `v7.2-rc7` resolves on linux-stable today
(checked 2026-08-26). It is recorded anyway, because it is what the pinned
revision *does*, and `preflight.sh` asserts both halves so an Armbian edit to
either is caught rather than silently absorbed.

---

## Resolved values

| What | Value |
|---|---|
| Armbian branch | `bleedingedge` |
| `KERNEL_MAJOR_MINOR` | `7.2` |
| `LINUXFAMILY` | `rockchip64` |
| Kernel config source | `config/kernel/linux-rockchip64-bleedingedge.config` |
| Armbian patch dir for this family | `patch/kernel/archive/rockchip64-7.2/` |
| `KERNELSOURCE` (mainline default) | `https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git` |
| `KERNELSOURCE` (Armbian's, after the rc7 hook) | `https://github.com/torvalds/linux.git` |
| `KERNELBRANCH` (Armbian's) | `tag:v7.2-rc7` — an **explicit release candidate** |
| **This repository's pin** | **`v7.2`** = `8d3ae59288f1e7d58d76558a6ee96d533bc5019f` (tag object `237a1c39e8dfd3e1c6f1f023eea37a48ec04cc63`) |

### Why the pin is `v7.2` and not `v7.2-rc7`

Armbian's 7.2 arm still points at a release candidate because the `@TODO` in its
own comment — *"roll over to next MAJOR.MINOR … when it is released"* — has not
been actioned. `v7.2` final was tagged **2026-08-16**, one day *before*
`ARMBIAN_BUILD_REV`, so the rc is simply stale rather than deliberate.

Pinning a release candidate would mean gating this series against a kernel nobody
will ever run. So this repository takes the final tag. The substitution is safe
because everything else on this page is derived from `KERNEL_MAJOR_MINOR`, which
is `7.2` either way — the config name and the patch directory are identical.

The previous base (`edge` → `7.1`) needed a tag pin for a *different* reason:
`branch:linux-7.1.y` is a rolling branch, so "verified against whatever that was
this morning" is not verified against anything reproducible. Either way the
conclusion is the same — **pin a tag, never follow a branch**.

### Where the SHAs came from

Resolved 2026-08-26 by listing three remotes live, never from a cache or a
previous note:

```bash
git ls-remote https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git \
    refs/tags/v7.2 'refs/tags/v7.2^{}'
git ls-remote https://github.com/gregkh/linux.git   refs/tags/v7.2 'refs/tags/v7.2^{}'
git ls-remote https://github.com/torvalds/linux.git refs/tags/v7.2 'refs/tags/v7.2^{}'
```

All three returned the same two SHAs, byte-identical:

| | |
|---|---|
| `refs/tags/v7.2` (annotated tag object) | `237a1c39e8dfd3e1c6f1f023eea37a48ec04cc63` |
| `refs/tags/v7.2^{}` (peeled commit) | `8d3ae59288f1e7d58d76558a6ee96d533bc5019f` |

`KERNEL_MIRROR` therefore stays `gregkh/linux` — it carries `v7.2` with the same
tag object and the same peeled commit, so no `torvalds/linux` fallback is
configured. Re-check on the next bump rather than assuming either way.

`scripts/apply.sh` refuses to proceed if `v7.2` in the tree it is handed does not
resolve to **both** the pinned commit and the pinned annotated-tag object, so a
moved, re-created or spoofed tag fails loudly instead of producing a green run
against the wrong source. The peeled commit alone cannot detect a tag object that
was re-created — re-signed, re-dated, re-worded — while still pointing at the
same commit, and the tag object is what a signature is verified against.

**Consequence for downstream consumers.** The image pipeline must pin the same
tag rather than following Armbian's branch, otherwise it will eventually build a
kernel this series was never tested against. Consuming
[`kernel-pin.env`](../kernel-pin.env) directly is the intended way to stay in sync
— it is plain `KEY="value"` lines, sourceable from `bash` and trivially parseable
from anything else.

---

## What `preflight.sh` gates, and what it only prints

| Check | Gating? |
|---|---|
| board → `BOARDFAMILY` | **yes** |
| board `KERNEL_TARGET` | no — printed as `info` |
| family config has no `bleedingedge)` arm of its own | **yes** |
| `KERNEL_MAJOR_MINOR` on the branch arm | **yes** |
| `LINUXFAMILY` on the branch arm | **yes** |
| `LINUXCONFIG`, with `$BRANCH` expanded | **yes** |
| the resolved config file exists at the revision | **yes** |
| `KERNELBRANCH`, against the **explicit** 7.2 arm | **yes** |
| `KERNELSOURCE`, against the hook keyed on that branch | **yes** |
| this repo's own `KERNEL_TAG` / `KERNEL_COMMIT` | no — printed; `apply.sh` proves it |

### The `KERNELBRANCH` comparison was reworked for this base

Worth knowing if you are reading a `git blame` here. While this repo tracked
`edge` → `7.1`, `preflight.sh` compared `KERNELBRANCH_ARMBIAN` against the
**rolling default** and treated the appearance of an explicit arm as drift —
correct then, because `7.1` has no arm and an arm appearing would have changed
the resolution entirely.

That logic is exactly wrong for `7.2`, which resolves *through* an explicit arm:
it would have compared the pin against a default that never runs and reported
permanent, unfixable drift. The script now reads the explicit arm **first** and
falls back to the rolling default only when there genuinely is no arm for this
`MAJOR.MINOR`, so both shapes are handled and a future 7.2 rollover to a final
tag will register as ordinary drift rather than as a broken check.

---

## Relationship to the shipped image

The shipped CeraLive image is **not** on `bleedingedge`. It is locked to the
Armbian **vendor** BSP kernel (`rk-6.1-rkr5.1`, package
`linux-image-vendor-rk35xx`), for the reasons recorded in the image pipeline's own
kernel-currency notes: the vendor BSP already provides HDMI-RX and mature
Rockchip MPP H.265 encode.

This repository targets the mainline track because that is where these patches are
meaningful — the vendor BSP has its own in-tree rkvenc/MPP stack and does not need
them. Nothing here changes the shipped image's kernel branch. Treat this series as
the mainline-track option, kept applying and audited, not as a pending migration.
