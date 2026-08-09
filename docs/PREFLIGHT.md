# Preflight — how the Armbian rk3588 `edge` kernel was resolved

Everything in [`kernel-pin.env`](../kernel-pin.env) was **read out of Armbian's
own configuration at a recorded revision**, not copied from a wiki or from a
previous investigation. This page shows the derivation so it can be re-checked.

Re-run it yourself at any time:

```bash
scripts/preflight.sh          # against the pinned ARMBIAN_BUILD_REV
scripts/preflight.sh --head   # against armbian/build's current main
```

The `--head` form is the one that answers *"has Armbian moved `edge` since this
was pinned?"*, and it is what CI runs on a schedule.

---

## Resolved on 2026-07-31

**Framework revision:** `armbian/build` `main` @ `587b6f2c0a867859ca3f323f6008bee9e3ef1553`
(committed 2026-07-31, and the tip of `main` at the time of this audit).

> A prior CeraLive exploration had recorded `edge = 7.1` at framework revision
> `fb027e3`. Both halves were re-verified here rather than assumed. `fb027e3e992e…`
> is a real `armbian/build` commit from 2026-07-30 — one day before this one — so
> that figure was current when it was taken, and the `edge = 7.1` mapping it
> recorded **still holds**. The framework SHA is what moved; the mapping did not.

### Boards

Both CeraLive RK3588 targets resolve to the same Armbian family, so one mapping
covers both.

| Armbian board config | `BOARDFAMILY` | `KERNEL_TARGET` |
|---|---|---|
| `config/boards/rock-5b-plus.conf` | `rockchip-rk3588` | `vendor,current,edge` |
| `config/boards/orangepi5-plus.conf` | `rockchip-rk3588` | `current,edge,vendor` |

`edge` is a supported target on both.

### The derivation chain (four files, in order)

**1. `config/sources/families/rockchip-rk3588.conf`**

Line 10 sources the common include *before* anything else:

```bash
source "${BASH_SOURCE%/*}/include/rockchip64_common.inc"
```

Its own `case $BRANCH` then handles **only `legacy` and `vendor`**. There is no
`edge)` arm. This is the step that is easy to get wrong: reading this file alone
suggests `edge` is unsupported, when in fact `edge` simply keeps whatever the
include already set. `scripts/preflight.sh` asserts the absence of an `edge)` case
so that a future Armbian change here cannot silently invalidate the chain.

**2. `config/sources/families/include/rockchip64_common.inc`**

```bash
edge)
    declare -g KERNEL_MAJOR_MINOR="7.1"
    declare -g LINUXFAMILY=rockchip64
    declare -g LINUXCONFIG='linux-rockchip64-'$BRANCH
    ;;
```

For context, the neighbouring arms are `current` → `6.18` and `bleedingedge` → `7.2`.

**3. `lib/functions/configuration/main-config.sh`**

No `KERNELSOURCE` is set for `edge`, so it falls through to the mainline source.
For the default (non-China) region:

```bash
declare -g -r MAINLINE_KERNEL_SOURCE='https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git'
```

**4. `config/sources/mainline-kernel.conf.sh`**

No `KERNELBRANCH` is set either, so the last-resort hook decides:

```bash
function mainline_kernel_decide_version__900_defaults() {
    [[ -n "${KERNELBRANCH}" ]] && return 0
    declare -g KERNELBRANCH="branch:linux-${KERNEL_MAJOR_MINOR}.y"
}
```

→ `branch:linux-7.1.y`.

Note that `7.2` (`bleedingedge`) *does* have an explicit override in this file
(`tag:v7.2-rc4`, sourced from `torvalds/linux`). `7.1` does not, so `edge` gets the
rolling stable branch. `preflight.sh` watches for an override appearing on this
version, because that would change the resolution entirely.

---

## Resolved values

| What | Value |
|---|---|
| Armbian branch | `edge` |
| `KERNEL_MAJOR_MINOR` | `7.1` |
| `LINUXFAMILY` | `rockchip64` |
| Kernel config source | `config/kernel/linux-rockchip64-edge.config` |
| Armbian patch dir for this family | `patch/kernel/archive/rockchip64-7.1/` |
| `KERNELSOURCE` | `https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git` |
| `KERNELBRANCH` (Armbian's) | `branch:linux-7.1.y` — a **rolling branch** |
| **This repository's pin** | **`v7.1.7`** = `c7ba9d6de43e9d9bd755b1f3c19501a38898c6b6` (tag object `c8fde2689e91a16e9d4b11fe3b08e45c89870585`) |

### Why a tag is pinned when Armbian uses a branch

Armbian tracks `linux-7.1.y`, which moves with every stable release. A patch series
verified against "whatever `linux-7.1.y` was that morning" is not verified against
anything reproducible. So this repository pins the exact stable tag that was the
tip of `linux-7.1.y` when the pin was last taken — `v7.1.7`, released 2026-08-06 —
and the CI gate applies against that tag and no other. The previous pin was
`v7.1.5` (released 2026-07-24); the move is ledgered in
[`REBASE-v7.1.7.md`](REBASE-v7.1.7.md).

`scripts/apply.sh` refuses to proceed if `v7.1.7` in the tree it is handed does not
resolve to **both** the pinned commit and the pinned annotated-tag object, so a
moved, re-created or spoofed tag fails loudly instead of producing a green run
against the wrong source.

**Consequence for downstream consumers.** The image pipeline must pin the same tag
rather than following `linux-7.1.y`, otherwise it will eventually build a kernel
this series was never tested against. Consuming
[`kernel-pin.env`](../kernel-pin.env) directly is the intended way to stay in sync
— it is plain `KEY="value"` lines, sourceable from `bash` and trivially parseable
from anything else.

---

## Relationship to the shipped image

The shipped CeraLive image is **not** on `edge`. It is locked to the Armbian
**vendor** BSP kernel (`rk-6.1-rkr5.1`, package `linux-image-vendor-rk35xx`), for
the reasons recorded in the image pipeline's own kernel-currency notes: the vendor
BSP already provides HDMI-RX and mature Rockchip MPP H.265 encode.

This repository targets `edge` because that is where these mainline patches are
meaningful — the vendor BSP has its own in-tree rkvenc/MPP stack and does not need
them. Nothing here changes the shipped image's kernel branch. Treat this series as
the mainline-track option, kept applying and audited, not as a pending migration.
