# Provenance and licence audit

**Audited:** 2026-07-31
**Subject:** `rcawston/rockchip-rk3588-mainline-patches` at `e13a311d8ee5e8ed92ec3d4a57c21f766c61d660`, as imported into this repository.

This is a **factual ledger**, not legal advice and not a clearance. It records
what was examined, what was found, and which questions remain open. No lawyer has
reviewed it and no legal sign-off is claimed or implied. Where something is
uncertain it is written down as uncertain.

---

## 1. What this repository redistributes

| Kind | Where | What it is |
|------|-------|-----------|
| Unified diffs, verbatim | `upstream/*.patch` | Ross Cawston's original `diff -ruN` files, byte-for-byte as published |
| Unified diffs, repackaged | `patches/*.patch` | The same diffs wrapped in git mailbox headers, with context re-anchored for `v7.1.5`. Every added/removed line is byte-identical to `upstream/` — enforced by `scripts/verify-payload-parity.py` |
| Device-tree overlay | `overlays/rockchip-rk3588-rkvenc-mpp.dts` | Ross Cawston's overlay, verbatim |
| CeraLive-authored | `scripts/`, `docs/`, `rebase/`, `kernel-pin.env`, `.github/` | CeraLive packaging, tooling, and documentation |

No compiled kernel, `.deb`, or binary blob is redistributed. This repository
produces patch text only.

---

## 2. Upstream repository: no collection licence

`rcawston/rockchip-rk3588-mainline-patches` has **no `LICENSE` file** at the
imported revision. The tree at `e13a311` contains exactly six blobs — four
`.patch` files, `README.MD`, and the `.dts` overlay — and nothing else. The GitHub
API reports `"license": null` for the repository, which is consistent.

So the repository **as a collection** carries no stated licence grant. Licensing
information exists only *inside* the individual files, which is what the rest of
this document examines.

---

## 3. Per-file licence markers introduced by the series

### 3.1 New files added by `0001` (the VEPU580 / rkvenc encoder)

| File | SPDX identifier | Copyright line(s) | Stated origin |
|------|-----------------|-------------------|---------------|
| `drivers/media/platform/rockchip/rkvenc/rkvenc_drv.c` | `(GPL-2.0+ OR MIT)` | Rockchip Electronics Co., Ltd. 2023; Ross Cawston 2026 | Ported from Rockchip BSP `mpp_rkvenc2.c` |
| `drivers/media/platform/rockchip/rkvenc/rkvenc_hw.c` | `(GPL-2.0+ OR MIT)` | Rockchip Electronics Co., Ltd. 2023 | Ported from Rockchip BSP `mpp_rkvenc2.c` |
| `drivers/media/platform/rockchip/rkvenc/rkvenc_hw.h` | `(GPL-2.0+ OR MIT)` | Rockchip Electronics Co., Ltd. 2023 | Ported from Rockchip BSP `mpp_rkvenc2.c` / `mpp_common.h` |
| `drivers/media/platform/rockchip/rkvenc/rkvenc_iommu.c` | `(GPL-2.0+ OR MIT)` | Rockchip Electronics Co., Ltd. 2023 | Ported from Rockchip BSP `mpp_iommu.c` |
| `drivers/media/platform/rockchip/rkvenc/rkvenc_service.c` | `(GPL-2.0+ OR MIT)` | Rockchip Electronics Co., Ltd. 2023 | Ported from Rockchip BSP `mpp_service.c` / `mpp_common.c` |
| `drivers/media/platform/rockchip/rkvenc/rkvenc_task.c` | `(GPL-2.0+ OR MIT)` | Rockchip Electronics Co., Ltd. 2023 | Ported from Rockchip BSP `mpp_common.c` |
| `include/uapi/linux/rkvenc.h` | `((GPL-2.0+ WITH Linux-syscall-note) OR MIT)` | Rockchip Electronics Co., Ltd. 2023 | Ported from Rockchip BSP `rk-mpp.h` |
| `drivers/media/platform/rockchip/rkvenc/Kconfig` | **none** | none | — |
| `drivers/media/platform/rockchip/rkvenc/Makefile` | **none** | none | — |

Module metadata in `rkvenc_drv.c`:

```c
MODULE_DESCRIPTION("Rockchip VEPU580 (RKVENC v2) H.265/H.264/JPEG encoder driver");
MODULE_LICENSE("Dual MIT/GPL");
MODULE_AUTHOR("Rockchip Electronics Co., Ltd.");
```

`MODULE_LICENSE("Dual MIT/GPL")` is a recognised kernel value and agrees with the
`(GPL-2.0+ OR MIT)` SPDX tag: the module is GPL-compatible, so it will not taint
the kernel and it may use `EXPORT_SYMBOL_GPL` symbols.

`overlays/rockchip-rk3588-rkvenc-mpp.dts` also carries `SPDX-License-Identifier: (GPL-2.0+ OR MIT)`.

### 3.2 Files modified by `0001`, `0002`, `0003`, `0005`

Every other file the series touches already exists in mainline and keeps its own
mainline licence. Nothing in the series alters an SPDX line. Verified at `v7.1.5`:

| File | Existing mainline SPDX | Touched by |
|------|------------------------|-----------|
| `arch/arm64/boot/dts/rockchip/rk3588-base.dtsi` | `(GPL-2.0+ OR MIT)` | 0001 |
| `drivers/iommu/rockchip-iommu.c` | `GPL-2.0-only` | 0001 |
| `drivers/media/platform/rockchip/Kconfig` | `GPL-2.0-only` | 0001 |
| `drivers/media/platform/rockchip/Makefile` | `GPL-2.0-only` | 0001 |
| `drivers/media/platform/synopsys/hdmirx/snps_hdmirx.c` | `GPL-2.0` | 0002, 0003, 0005 |
| `drivers/media/platform/synopsys/hdmirx/snps_hdmirx.h` | `GPL-2.0` | 0005 |
| `drivers/media/platform/synopsys/hdmirx/Kconfig` | `GPL-2.0` | 0005 |

Patches `0002`, `0003` and `0005` add **no new files** and introduce no new
licence claim of any kind. They are ordinary modifications to GPL-2.0 mainline
files, and the licensing question below concerns `0001` only.

---

## 4. Vendor-BSP origin: verified, not assumed

The headers say "Ported from Rockchip BSP …". That claim was checked against the
actual Rockchip BSP sources, via the Armbian BSP mirror
`armbian/linux-rockchip`, branch `rk-6.1-rkr5.1`:

| BSP original | SPDX in the BSP source | Copyright in the BSP source |
|--------------|------------------------|------------------------------|
| `drivers/video/rockchip/mpp/mpp_rkvenc2.c` | `(GPL-2.0+ OR MIT)` | (c) 2021 Rockchip Electronics Co., Ltd. |
| `drivers/video/rockchip/mpp/mpp_service.c` | `(GPL-2.0+ OR MIT)` | (c) 2019 Fuzhou Rockchip Electronics Co., Ltd |
| `drivers/video/rockchip/mpp/mpp_common.c` | `(GPL-2.0+ OR MIT)` | (c) 2019 Fuzhou Rockchip Electronics Co., Ltd |
| `drivers/video/rockchip/mpp/mpp_common.h` | `(GPL-2.0+ OR MIT)` | (c) 2019 Fuzhou Rockchip Electronics Co., Ltd |
| `drivers/video/rockchip/mpp/mpp_iommu.c` | `(GPL-2.0+ OR MIT)` | (c) 2019 Fuzhou Rockchip Electronics Co., Ltd |
| `include/uapi/linux/rk-mpp.h` | `((GPL-2.0+ WITH Linux-syscall-note) OR MIT)` | (C) 2023 Rockchip Electronics Co., Ltd. |

**This is the single most important finding in this audit.** Every SPDX tag the
ported files claim is *the same tag the Rockchip BSP original already carried*,
including the UAPI header's `Linux-syscall-note` variant. The dual-licence claim
is therefore **inherited from the copyright holder's own header**, not invented
downstream by the porter. That is the ordinary, expected shape of a vendor-code
port, and it settles whether a `MIT` claim on this kernel code is genuine.

### 4.1 Attribution discrepancies (minor, recorded for completeness)

Two things do not line up exactly, neither of which changes the licence:

1. **Copyright years and entity name were normalised.** The ports uniformly say
   `Copyright (C) 2023 Rockchip Electronics Co., Ltd.` The originals say 2019 or
   2021, and four of them say *Fuzhou* Rockchip Electronics Co., Ltd. The port
   flattened both. This understates the age of the original work and drops the
   "Fuzhou" entity name.
2. **The named BSP author is not carried forward.** `mpp_rkvenc2.c` credits
   `Ding Wei, leo.ding@rock-chips.com`; no ported file mentions them, and
   `MODULE_AUTHOR` names only the company.

Neither is a licence defect — the corporate copyright holder is still named and
the SPDX tags match — but both are attribution accuracy issues in the upstream
port. **This repository does not modify patch content** (see §6), so they are
recorded rather than corrected.

---

## 5. Redistribution basis

**GPL-2.0 distribution of this series is the safe, ordinary case**, for the
following reasons:

- The Linux kernel is `GPL-2.0-only` (with the syscall-note exception for UAPI).
- A patch against the kernel is a derivative of the kernel, so distributing it
  under GPL-2.0 terms is exactly what the licence contemplates.
- Every new file carries `(GPL-2.0+ OR MIT)`, a disjunction. A recipient may elect
  either branch. Electing `GPL-2.0+` — and then, as GPL-2.0+ permits, using it at
  version 2 — combines cleanly into the `GPL-2.0-only` kernel.
- The combined work (kernel + this series) is therefore treated as
  **GPL-2.0-only**, and this repository is distributed on that basis.

### 5.1 The MIT-claim caveat

The `MIT` half of the disjunction is a **real, unresolved ambiguity**:

- **The upstream patch repository has no `LICENSE` file at all** (§2). So there is
  no collection-level grant that says "this repository is MIT" or anything else.
  Anyone who wants to rely on the MIT branch is relying purely on per-file SPDX
  headers in a repository whose owner made no repository-level licence statement.
- **The SPDX tag is inherited, which is evidence but not proof.** Rockchip's own
  BSP files were verified to carry `(GPL-2.0+ OR MIT)` (§4). That is strong
  evidence the dual grant is genuine and originates with the copyright holder. It
  is *not* proof that every line in the ported files came from those specific
  dual-licensed BSP files — a port is a rewrite, and no line-by-line derivation
  audit of ~4,200 lines of driver code against the BSP originals was performed.
- **A GPL-2.0-only line anywhere in the port would silently collapse the
  disjunction.** If any portion were in fact taken from GPL-2.0-only kernel code
  (for example, boilerplate borrowed from another in-tree driver), the MIT branch
  could not be validly asserted for the file containing it, regardless of the
  header. This has not been ruled out.
- **`MODULE_LICENSE("Dual MIT/GPL")` proves nothing about MIT.** It is a
  kernel-internal taint/symbol-visibility marker. It tells the kernel the module is
  GPL-compatible. It is not a licence grant and carries no legal weight of its own.

**Practical consequence for CeraLive: none, today.** CeraLive uses the GPL-2.0
branch, ships the series as kernel patches, and makes **no MIT claim** and takes
no MIT-dependent action anywhere. Relying on the MIT branch — for instance to
link this code into something proprietary — would require an independent
derivation audit and legal review. This document is not that.

---

## 6. What this fork does and does not change

- Patch behaviour is **not** modified. `patches/` is a repackaging of
  `upstream/`; every added and removed line is byte-identical, mechanically
  enforced by `scripts/verify-payload-parity.py` in CI.
- No SPDX identifier, copyright line, or `MODULE_LICENSE` value is added,
  removed, or altered.
- Nothing is relicensed. `LICENSE` in this repository describes the terms the
  imported material already carries; it grants nothing new.
- This series is **not** claimed to be upstream-mergeable, or to have been or be
  offered to `rcawston` or to the Linux kernel. Upstream's own README states the
  encoder driver is "not intended for upstream merge".
- Full upstream git history and authorship are preserved: this repository is a
  GitHub fork of the source repository, and all eight upstream commits remain
  attributed to Ross Cawston.

---

## 7. Open questions (not closed by this audit)

1. Line-by-line derivation of the ~4,200 lines of ported rkvenc driver code
   against the Rockchip BSP originals. Not performed. This is what would be needed
   to rely on the MIT branch.
2. Whether Rockchip's BSP `(GPL-2.0+ OR MIT)` tags are themselves accurate for
   every line of *their* sources. Out of scope; the copyright holder's header is
   taken at face value.
3. `rkvenc/Kconfig` and `rkvenc/Makefile` ship with **no SPDX header**. In-tree
   these would be flagged by `scripts/checkpatch.pl`. Cosmetic, but it means two
   of the nine new files have no per-file licence marker at all and fall back to
   the (absent) collection licence. Not fixed here, because fixing it would mean
   editing patch content — see §6.
4. No legal review. None requested, none obtained, none implied.
