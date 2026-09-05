#!/usr/bin/env python3
"""Turn the raw patch sources into a git-am-able mailbox series.

Why this exists
---------------
upstream/*.patch are raw ``diff -ruN aa/ bb/`` output. They carry no mail headers,
so ``git am`` rejects them before it ever looks at a hunk -- the upstream README's
``git am /path/to/patches/*.patch`` instruction has never worked. Two of them also
carry macOS ``.DS_Store`` "Binary files ... differ" stanzas, which ``git apply``
refuses ("cannot apply binary patch ... without full index line") even once headers
exist.

On top of that, upstream targeted v6.19-rc8 and we target the tag in kernel-pin.env,
so a few context anchors have drifted. Those are re-anchored from an explicit,
reviewable table (rebase/<tag>.rules) -- never inline in this file.

Four lanes, one pipeline
-------------------------
``upstream/`` holds Ross Cawston's files verbatim. ``ceralive/`` holds first-party
patches this project authored, which have no upstream counterpart. ``backports/``
holds patches taken from mainline, a stable tree, or lore. ``island/`` holds the
already-generated mailbox members from a CeraLive rk3588-media-island release,
byte-preserved and re-headed only to join this repository's ordinal sequence. All
four lanes go through the same converter so that ``patches/`` stays fully generated.

Retirement, not deletion
------------------------
A source file is never deleted. Dropping a patch from the series MOVES it into
``retired/`` byte-unchanged and records a row in ``retired/REGISTRY.md``; that is
what keeps "``upstream/`` is byte-identical to what was imported" checkable even
after the series stops carrying one of those files. The membership check below
enforces the resulting invariant.

Guarantees
----------
* Deterministic: same inputs -> byte-identical output. ``--check`` relies on it.
* Behaviour-preserving by construction: a rule may only touch a CONTEXT line.
  Attempting to rewrite a '+'/'-' line raises. scripts/verify-payload-parity.py
  proves the result independently, per lane.
* Exactly-once membership, both directions: every ``*.patch`` under a source lane
  is either an active SERIES member or a registered retirement -- never both, and
  never neither. A new file dropped into a lane and forgotten is an ERROR, not a
  silent no-op.
* Upstream numbering (0001/0002/0003/0005, gap at 0004) is never renumbered, and a
  retired ordinal is never reused. First-party patches continue the same counter
  from 0006.
* kernel-pin.env is parsed the way bash reads it, inline ``#`` comments included,
  so a pinned coordinate cannot leak a comment fragment into generated metadata.

Usage
-----
    scripts/build-series.py            regenerate patches/
    scripts/build-series.py --check    rebuild into a temp dir and diff; non-zero
                                       exit if patches/ is stale or hand-edited
"""

from __future__ import annotations

import argparse
import filecmp
import hashlib
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATCHES_DIR = ROOT / "patches"
REBASE_DIR = ROOT / "rebase"
PIN_FILE = ROOT / "kernel-pin.env"
RETIRED_DIR = ROOT / "retired"
REGISTRY_FILE = RETIRED_DIR / "REGISTRY.md"

UPSTREAM = "upstream"
CERALIVE = "ceralive"
BACKPORTS = "backports"
ISLAND = "island"
SOURCE_DIRS = {
    UPSTREAM: ROOT / UPSTREAM,
    CERALIVE: ROOT / CERALIVE,
    BACKPORTS: ROOT / BACKPORTS,
    ISLAND: ROOT / ISLAND,
}

# overlays/ is NOT a source lane -- nothing in it becomes a series member -- but a
# file may still leave it, and leaving is always a retirement. Registering it needs
# a lane name, so the registry accepts this one in addition to the source lanes and
# refuses it an ordinal (see NO_ORDINAL).
OVERLAYS = "overlays"
RETIRABLE_LANES = {**SOURCE_DIRS, OVERLAYS: ROOT / OVERLAYS}

# Only *.patch is a series candidate. upstream/README.MD and the per-lane READMEs
# live beside the patches and are not part of any lane's membership.
LANE_GLOB = "*.patch"

REGISTRY_COLUMNS = ("Patch", "Lane", "Ordinal", "Retired", "Kernel tag", "Reason")
REGISTRY_RULE_RE = re.compile(r"^:?-{3,}:?$")
# An artifact that never held a series slot records its ordinal as this, rather
# than borrowing a number it never had. `0` would collide with nothing and still
# be a lie; a slot is either held or it is not.
NO_ORDINAL = "-"
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REVISION_RE = re.compile(r"^v[0-9]+$")
# CalVer, as the island releases it: vYYYY.M.P.
ISLAND_TAG_RE = re.compile(r"^v[0-9]{4}\.[0-9]+\.[0-9]+$")

# Slot count, not member count, and it never shrinks. 0004 was never published
# upstream and we keep the gap so our files line up 1:1 with theirs; 0007 and
# 0023-0025 are retired ordinals whose slots stay burned, as are the ten rkvenc
# slots the island release superseded. Every later ordinal continues the same
# counter regardless of lane: 0010-0012 into backports/, 0031-0039 into island/,
# everything else into ceralive/.
#
# 30 slots existed before the island lane; the current release adds 9 members at
# 0031-0039; the EDID guard adds 0040. Retiring ten members
# out of those first 30 slots does NOT reduce it: an N/39 subject counts slots.
SERIES_TOTAL = 40
ISLAND_ORDINAL_OFFSET = 30

DS_STORE_RE = re.compile(r"^Binary files .*\.DS_Store .* differ$")
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")


# A first-party patch has no originating commit anywhere, so the mbox delimiter
# carries the null object id rather than a borrowed or invented one.
NULL_OID = "0" * 40

# An UNMERGED lore posting has no commit id at all. NULL_OID would be a lie with
# 40 hex digits, a parent SHA would assert a merge that did not happen, and the
# stable-tree `commit <sha> upstream.` marker would assert both. So this lane
# carries a sentinel that cannot be mistaken for an object id, and the generated
# header states the absence of an identity instead of inventing one.
LORE_POSTING = "lore-posting"

# An island member has no kernel commit either. The island release DOES name a
# commit, but it is a commit in CERALIVE/rk3588-media-island -- not in the history
# this delimiter's field is for -- so putting it here would assert a kernel
# identity that does not exist, exactly the way NULL_OID would. The release
# coordinates travel in Island(...) instead, where they are labelled.
ISLAND_RELEASE = "island-release"


@dataclass(frozen=True)
class Island:
    """Immutable release coordinates for a byte-preserved island/ member."""

    tag: str
    commit: str
    asset_sha256: str


@dataclass(frozen=True)
class Backport:
    """Where a backports/ patch actually came from.

    The upstream/ lane can hard-code one credit line because every file in it has
    the same origin. A backport does not: each one is lifted from its own commit
    and its own list posting, so the origin travels with the patch.
    """

    upstream_subject: str
    lore_msgid: str  # Message-ID as it appears in a lore URL, no angle brackets
    note: tuple[str, ...] = ()


@dataclass(frozen=True)
class LorePosting:
    """Where an UNMERGED backports/ patch came from, and how that is checkable.

    Every field is mandatory. The two thread digests are attestations of the exact
    archive response the import consumed: ``thread_compressed_sha256`` covers the
    ``t.mbox.gz`` bytes as served, and ``thread_mbox_sha256`` covers the mailbox
    those bytes decompress to. They are different domains and are never
    interchangeable. ``canonical_patch_sha256`` covers this one posting's
    canonical mail, archived in-tree at ``canonical_mail`` so the digest can be
    recomputed by anyone, at any time, without the network.
    """

    lore_msgid: str
    revision: str
    posted_date: str
    upstream_subject: str
    thread_compressed_sha256: str
    thread_mbox_sha256: str
    canonical_patch_sha256: str
    canonical_mail: str
    review_state: str
    note: tuple[str, ...] = ()


@dataclass(frozen=True)
class Patch:
    """One member of the series."""

    filename: str
    ordinal: int
    subject: str
    provenance: str | Island
    author: str
    date: str
    origin: str = UPSTREAM
    rationale: tuple[str, ...] = ()  # first-party lane only: why this patch exists
    backport: Backport | None = None  # backports lane: merged-commit provenance
    lore: LorePosting | None = None  # backports lane: unmerged-posting provenance


SERIES: tuple[Patch, ...] = (
    Patch(
        filename="0002-rockchip-rk3588-hdmirx-edid-fix-v1.patch",
        ordinal=2,
        subject="media: synopsys: hdmirx: make a written EDID visible to the HDMI source",
        provenance="8478ca74ad2f340feb7f443acbb669292497cf3e",
        author="Ross Cawston <rcawston@users.noreply.github.com>",
        date="Mon, 9 Feb 2026 12:10:15 -0800",
    ),
    Patch(
        filename="0003-rockchip-rk3588-hdmirx-plugout-fix-v1.patch",
        ordinal=3,
        subject="media: synopsys: hdmirx: fix buffer overflow on repeated HDMI-RX replug",
        provenance="90b3a5c579ffb0ac164e4cea7163228a864ef0c4",
        author="Ross Cawston <rcawston@users.noreply.github.com>",
        date="Mon, 9 Feb 2026 14:35:17 -0800",
    ),
    Patch(
        filename="0005-rockchip-rk3588-hdmirx-audio.patch",
        ordinal=5,
        subject="media: synopsys: hdmirx: add HDMI-RX audio capture support",
        provenance="e13a311d8ee5e8ed92ec3d4a57c21f766c61d660",
        author="Ross Cawston <rcawston@users.noreply.github.com>",
        date="Wed, 1 Jul 2026 14:19:29 -0700",
    ),
    Patch(
        filename="0006-rk3588-hdmirx-audio-sound-card.patch",
        ordinal=6,
        subject="arm64: dts: rockchip: rk3588: bind the HDMI-RX audio codec to a sound card",
        provenance=NULL_OID,
        author="Andres Cera <andres.cera@hotmail.com>",
        date="Sun, 2 Aug 2026 12:00:00 -0500",
        origin=CERALIVE,
        rationale=(
            "0005 gives snps_hdmirx its driver-side audio half: it registers an ASoC",
            "hdmi-audio-codec child device under hdmi_receiver@fdee0000 and drives the",
            "receiver's audio FIFO, ACR-derived sample rate and recovered audio clock.",
            "It touches no device tree, and ALSA does not instantiate a card for a bare",
            "codec. On a Rock 5B+ running the full series the codec device is bound with",
            "no cable attached --",
            "",
            "  /sys/devices/platform/fdee0000.hdmi_receiver/hdmi-audio-codec.7.auto",
            "",
            "-- while /proc/asound/cards lists only the USB dongle, the onboard es8316",
            "and hdmi0/hdmi1, which are the two HDMI *transmitters*. There is no",
            "hdmirx-sound node, so HDMI-IN embedded audio cannot be captured at all.",
            "",
            "Three DT facts are missing, all of them here:",
            "",
            "  1. hdmi_receiver has no #sound-dai-cells, so it cannot be named as a DAI",
            "     provider. simple-audio-card resolves sound-dai through",
            "     of_parse_phandle_with_args(..., \"#sound-dai-cells\", ...), and ASoC's",
            "     soc_component_to_node() falls back to a component's parent of_node --",
            "     which is exactly how &hdmi0 already stands in for its own",
            "     hdmi-audio-codec child. With zero cells the first DAI is selected,",
            "     i2s-hifi, since hdmi_codec_probe() registers i2s before spdif.",
            "  2. There is no card node binding that codec to a CPU DAI.",
            "  3. i2s7_8ch -- the capture-only I2S the RK3588 receiver feeds, per the",
            "     Rockchip BSP's own hdmiin-sound wiring -- is left disabled on both",
            "     boards.",
            "",
            "Add the card as a disabled-by-default simple-audio-card next to the existing",
            "hdmi0/hdmi1 ones and enable it, with i2s7_8ch, on the two boards that already",
            "enable hdmi_receiver: rk3588-rock-5b.dtsi (Rock 5B, 5B+, 5T) and",
            "rk3588-orangepi-5-plus.dts.",
            "",
            "The receiver recovers its audio clock from the incoming stream, so the codec",
            "is bitclock and frame master and i2s7_8ch runs as consumer; mclk-fs = 128",
            "matches the BSP and the fs*128 rate 0005 programs on the \"audio\" clock.",
            "i2s7_8ch declares only a \"rx\" DMA, so rockchip_i2s_tdm_init_dai() marks it",
            "capture-only and the link resolves to a single capture stream.",
        ),
    ),
    Patch(
        filename="0009-dma-buf-heaps-add-system-uncached-dma-heap.patch",
        ordinal=9,
        subject="dma-buf: heaps: add a system-uncached heap",
        provenance=NULL_OID,
        author="Andres Cera <andres.cera@hotmail.com>",
        date="Sun, 9 Aug 2026 12:00:00 -0500",
        origin=CERALIVE,
        rationale=(
            "*** VALIDATED on Rock 5B+ (2026-08-09) -- UNVALIDATED on Orange Pi 5+. ***",
            "/dev/dma_heap/system-uncached was confirmed a genuine second heap (minor",
            "250,1 vs system's 250,0, its own /sys/class/dma_heap entry) that does NOT",
            "draw from CMA: holding a 1080p + 4K allocation open left CmaFree unchanged",
            "at 25,504 kB, while the identical pair from the CMA heap dropped it to",
            "10,312 kB. Encoded output was byte-identical across 5 repeats, 3",
            "resolutions, a reboot and 5.2 GiB of memory pressure, decoding clean with",
            "CABAC in use. See docs/BOARD-QUALIFICATION.md for the full transcript and",
            "image-building-pipeline's",
            ".omo/evidence/image-pipeline-quality/hardware-validation-round1.md for the",
            "raw session evidence. Orange Pi 5+ has never run this image at all, and no",
            "real HDMI capture source was attached during this run -- do NOT read this",
            "marker as a claim that MPP hardware encode is validated fleet-wide or that",
            "the full capture-to-encode path with live video is proven.",

            "*** HARDWARE PROOF WAS MANDATORY FOR THIS PATCH, AND HAS NOW BEEN GIVEN ON",
            "ONE BOARD. *** Everything else in this series can be argued from source.",
            "This one could not, for the reason stated plainly below under CACHE",
            "ALIASING: a compile proves the heap exists, and a heap that exists while",
            "getting cache maintenance subtly wrong produces intermittent, silent",
            "corruption in the video path rather than an error. The checklist that",
            "was run to clear this marker is docs/BOARD-QUALIFICATION.md.",
            "",
            "Origin: the root-cause analysis recorded as defects 1 and 3 of 3 in the CeraLive",
            "image-building-pipeline AGENTS.md KNOWN ISSUE on MPP hardware video encode not",
            "working on the edge kernel -- a Rock 5B+ board diagnosis, 2026-08-02. 0008 in",
            "this series is defect 2; this patch is the other two, which share one cause.",
            "",
            "Defect 1: mpph264enc does not register at all. librockchip-mpp's dma-heap",
            "allocator table hard-codes the heap name system-uncached for an uncached",
            "allocation and has no environment override. Mainline registers system,",
            "default_cma_region and reserved, so the H.264 HAL's init-time buffer allocation",
            "fails, mpp_init(MPP_CTX_ENC, AVC) fails, and the GStreamer plugin's registration",
            "probe skips the element. The board log names it exactly:",
            "os_allocator_dma_heap_open open dma heap type 0 system-uncached failed!",
            "",
            "Defect 3: even with a corrected mapping, MPP performs no CPU cache maintenance",
            "on a heap it believes is uncached. Handed cached memory it produced different",
            "output sizes for byte-identical input (1280x720 x60: 231047 bytes, then 161997)",
            "and intermittent CABAC decode failures. So registering the name alone is not",
            "enough -- the memory behind it has to actually be uncached, which is why these",
            "are one patch and not two.",
            "",
            "The heap is the system heap's page allocation with three changes, in the shape",
            "the ACK/Rockchip uncached heap has carried for years:",
            "",
            "  1. Its mappings are non-cacheable. mmap() and the internal vmap() both take",
            "     pgprot_writecombine(), which is Normal-NC on arm64.",
            "  2. Its pages are cleaned to the point of coherency exactly once, at",
            "     allocation, with arch_dma_prep_coherent(). __GFP_ZERO zeroes them through",
            "     the cacheable linear map, so without that clean the buffer starts life",
            "     with dirty lines that can evict on top of encoder output later.",
            "  3. The CPU-sync steps become no-ops ONLY where the memory is genuinely",
            "     uncached: DMA_ATTR_SKIP_CPU_SYNC on map and unmap, and the",
            "     dma_sync_sgtable_for_{cpu,device}() loops in begin/end_cpu_access skipped.",
            "     The cached system heap keeps every one of them, unchanged.",
            "",
            "CACHE ALIASING -- the honest limit, and the reason for the marker above. The",
            "kernel's cacheable linear-map alias of these pages is NOT torn down; only the",
            "heap's own mappings are non-cacheable. On arm64 a Normal-NC and a",
            "Normal-Cacheable alias of the same page are architecturally permitted to lose",
            "coherency, and nothing in this patch or in the DMA API prevents a third party",
            "from touching the linear-map alias. In practice nothing does, which is why the",
            "ACK heap has shipped this way at scale -- but in practice is a claim about",
            "observed behaviour, and it has not been observed here. A wrong answer does not",
            "look like a crash; it looks like a frame that decodes on Tuesday.",
            "",
            "Behaviour deliberately NOT changed:",
            "",
            "  - The heap NAME is the whole userspace contract and is spelled exactly",
            "    system-uncached. A symlink, bind mount or mknod alias onto an existing heap",
            "    is explicitly not a substitute and was rejected: aliasing the system heap",
            "    hands MPP cached memory it will not synchronise, and aliasing the CMA heap",
            "    caps out below 1080p on a 32 MiB pool that fragments to a ~1.9 MiB largest",
            "    run against a ~3.1 MiB 1080p NV12 frame.",
            "  - Only the name is registered. The node's mode and ownership stay userspace",
            "    policy -- the image already ships 99-rk-device-permissions.rules matching",
            "    KERNEL==system-uncached -- and this patch does not encode any of it.",
            "  - No allocator policy is redesigned and no new userspace API is invented. The",
            "    page orders, the GFP flags, the sg_table layout and the ioctl are the system",
            "    heap's, untouched. The new heap is a second dma_heap_add() with its own",
            "    drvdata, which is the extension point the file already uses for",
            "    system_cc_shared.",
            "  - There is no fallback to cached memory on any path. A caller that opens this",
            "    heap gets uncached memory or gets an error, and the Kconfig symbol depends",
            "    on ARCH_HAS_DMA_PREP_COHERENT so an architecture that cannot honour that",
            "    cannot build the heap in the first place.",
            "",
            "Gated by its own symbol, CONFIG_DMABUF_HEAPS_SYSTEM_UNCACHED, rather than",
            "riding CONFIG_DMABUF_HEAPS_SYSTEM: a downstream, hardware-unvalidated heap",
            "should be separately switchable, and a dedicated symbol is what lets the image",
            "pipeline's verify-kernel-config.sh gate prove the heap survived olddefconfig",
            "into the shipped kernel instead of merely proving its parent did.",
        ),
    ),
    Patch(
        filename="0010-phy-rockchip-naneng-combphy-force-rterm-det-rdy.patch",
        ordinal=10,
        subject=(
            "phy: rockchip: naneng-combphy: force RX-termination detect ready "
            "for the TX-detect erratum"
        ),
        provenance=LORE_POSTING,
        author="Shawn Lin <shawn.lin@rock-chips.com>",
        date="Wed, 25 Mar 2026 15:23:03 +0800",
        origin=BACKPORTS,
        lore=LorePosting(
            lore_msgid="1774423383-36599-1-git-send-email-shawn.lin@rock-chips.com",
            revision="v1",
            posted_date="Wed, 25 Mar 2026 15:23:03 +0800",
            upstream_subject=(
                "phy: rockchip: naneng-combphy: Fix TX detect RX termination errata"
            ),
            thread_compressed_sha256=(
                "edcf4285fd7f02670ae5329f48d79a4536ede75439aa3ec60a497be4b47926eb"
            ),
            thread_mbox_sha256=(
                "c59343ef5f34882d49a1830272cbd293a08cad248cca8b1ff45494d0dd0d9abb"
            ),
            canonical_patch_sha256=(
                "b2ef18765558fb27ddbb00c14ed3fc40e93bbc200a45e337e864326973df249b"
            ),
            canonical_mail="backports/lore/U3/01.mbox",
            review_state=(
                "posted 2026-03-25, author Signed-off-by only; Vinod Koul asked for a "
                "Fixes: tag and an erratum reference on 2026-05-10 and the author has "
                "not answered. No Reviewed-by, no Nacked-by, no reroll."
            ),
            note=(
                "Matrix alias U3. Some naneng-combphy revisions fail to detect the peer",
                "receiver's RTERM at critical temperatures, so a PCIe link that should",
                "come up simply does not. The posting sets FORCE_RTERM_DET_RDY in",
                "PHYREG26 for every SoC whose cfg opts in, RK3588 included -- and RK3588",
                "is where CeraLive's NVMe and USB3 capture links live.",
                "",
                "Screened against v7.1.7: applies with no fuzz base-only AND stacked on",
                "top of this series, touches one file no other member touches, and",
                "introduces no symbol the base lacks (rockchip_combphy_updatel and the",
                "RK3568_PHYREG* block are already there; PHYREG26 is defined by the",
                "patch itself). Zero prerequisites.",
                "",
                "The two mainline commits that landed on this file since the posting --",
                "0b31f297557f (Consolidate SSC configuration) and be2b5b17b705 (Always",
                "configure SSC spread direction) -- are both absent from v7.1.7 and",
                "neither touches the RTERM path, so no landed fix supersedes this.",
                "",
                "The open maintainer question is about the commit message, not the",
                "payload: a Fixes: tag and an erratum reference change what the log says,",
                "not what the register write does. That is why this is carried and the",
                "still-being-argued candidates in the same screening round are not.",
            ),
        ),
    ),
    Patch(
        filename="0011-dw-hdmi-qp-acr-n-cts-helper.patch",
        ordinal=11,
        subject=(
            "drm/bridge: dw-hdmi-qp: use drm_hdmi_acr_get_n_cts() for audio N/CTS"
        ),
        provenance=LORE_POSTING,
        author="Simon Wright <simon@symple.nz>",
        date="Thu, 21 May 2026 19:36:47 +1200",
        origin=BACKPORTS,
        lore=LorePosting(
            lore_msgid="86fcf349-0a7a-4618-9001-612371b0f71b@symple.nz",
            revision="v3",
            posted_date="Thu, 21 May 2026 19:36:47 +1200",
            upstream_subject=(
                "[PATCH v3] drm/bridge: dw-hdmi-qp: use drm_hdmi_acr_get_n_cts() "
                "helper for audio N/CTS"
            ),
            thread_compressed_sha256=(
                "70168ad154f4c2e92c2042ba96ff2e185a65a83c6f1710f28160b59e772960c9"
            ),
            thread_mbox_sha256=(
                "9b2beae10fd643d26a1f286e33825fd8e36ba3c521acd3f9ed1e6f4bb753d54c"
            ),
            canonical_patch_sha256=(
                "c20e395c4c8a67b3aff0a18bd28fbffedba8f91f42eb99fda2bc7ad2e83c1108"
            ),
            canonical_mail="backports/lore/U5/01.mbox",
            review_state=(
                "Reviewed-by and Tested-by Cristian Ciocaltea (Collabora), 2026-06-03, "
                "on the patch itself: \"The patch looks good to me.\" No change was "
                "requested and no reroll followed."
            ),
            note=(
                "Matrix alias U5. A STANDALONE posting: no cover letter and no sibling",
                "patches -- the thread is the patch plus one review reply, and this",
                "series records it that way rather than inventing a 0/N identity for it.",
                "",
                "dw-hdmi-qp carried its own pre-computed N/CTS table, which disagrees",
                "with the shared helper for several TMDS rates and silently produces the",
                "wrong audio clock regeneration. The posting deletes the private table",
                "and calls drm_hdmi_acr_get_n_cts(), which v7.1.7 already exports from",
                "drivers/gpu/drm/display/drm_hdmi_helper.c -- so the symbol it needs is",
                "in the base and there are zero prerequisites.",
                "",
                "Screened against v7.1.7: applies with no fuzz base-only AND stacked.",
                "The only mainline commit on this file since the posting is fb145be7964d",
                "(Use the common TMDS char rate constant), which does not touch the N/CTS",
                "path and does not supersede this.",
            ),
        ),
    ),
    Patch(
        filename="0012-dw-hdmi-qp-audio-eopnotsupp.patch",
        ordinal=12,
        subject=(
            "drm/bridge: dw-hdmi-qp: return -EOPNOTSUPP from the audio hooks "
            "with no active TMDS rate"
        ),
        provenance=LORE_POSTING,
        author="Detlev Casanova <detlev.casanova@collabora.com>",
        date="Tue, 19 May 2026 14:00:11 -0400",
        origin=BACKPORTS,
        lore=LorePosting(
            lore_msgid="20260519-fix-hdmi-audio-warnings-v1-1-9608966c993f@collabora.com",
            revision="v1",
            posted_date="Tue, 19 May 2026 14:00:11 -0400",
            upstream_subject=(
                "[PATCH] drm/bridge: dw-hdmi-qp: Return -EOPNOTSUPP in HDMI audio "
                "functions"
            ),
            thread_compressed_sha256=(
                "5704fdbfe53ee5320e1cbc0cc1498ef982056008e0d46643b6b43bf06e7bf977"
            ),
            thread_mbox_sha256=(
                "0ddf71d9eefd23424355be91d994b362a464113d7fbe5ef3e5ddb8cc0b0dabd9"
            ),
            canonical_patch_sha256=(
                "ba499367da7479e4d68ca9473d23b479b741140e4656496701549c002e87b2d7"
            ),
            canonical_mail="backports/lore/U6/01.mbox",
            review_state=(
                "Tested-by Maud Spierings (2026-07-06, Orange Pi 5+) and Tested-by "
                "Diederik de Haas (2026-08-08). Sebastian Reichel (Collabora) asked "
                "only for a Fixes: tag on 2026-06-01; no change to the payload was "
                "requested, and the author nudged the thread on 2026-08-06."
            ),
            note=(
                "Matrix alias U6. With no mode set, dw_hdmi_qp_audio_prepare() returned",
                "-ENODEV, which ASoC treats as a real error and logs on every attempt:",
                "reporters counted hundreds of \"ASoC error (-19) at",
                "snd_soc_dai_prepare() on i2s-hifi\" lines filling dmesg on an idle board",
                "with nothing plugged into HDMI. -EOPNOTSUPP is the code ASoC reads as",
                "\"this link cannot do that right now\", so the condition stops being",
                "logged as a fault. dw_hdmi_qp_audio_enable() gets the same treatment,",
                "and additionally stops clearing the audio SW-disable bit when there is",
                "no active TMDS rate to clear it for.",
                "",
                "This matters here beyond log hygiene: a dmesg buffer flooded by a",
                "non-fault is a dmesg buffer that has dropped whatever the HDMI-RX",
                "capture path was trying to report, and this series' own audio work",
                "(0005/0006) is diagnosed from exactly that buffer.",
                "",
                "Screened against v7.1.7: applies with no fuzz base-only AND stacked,",
                "two hunks in one file, no new symbol, zero prerequisites. It touches",
                "the same file as 0011 and the two do not overlap -- 0011 rewrites the",
                "N/CTS table, this one the audio enable/prepare hooks -- and applying",
                "0011 then this one was verified clean in that order.",
            ),
        ),
    ),
    Patch(
        filename="0017-hdmirx-audio-lifecycle-and-clock-errors.patch",
        ordinal=17,
        subject=(
            "media: synopsys: hdmirx: fix the audio work and clock lifecycle "
            "under lockdep"
        ),
        provenance=NULL_OID,
        author="Andres Cera <andres.cera@hotmail.com>",
        date="Sun, 10 Aug 2026 13:00:00 -0500",
        origin=CERALIVE,
        rationale=(
            "MOTIVATION. hdmi-codec invokes ->hook_plugged_cb() under the ASoC",
            "card mutex, and the installed callback reports a jack under the",
            "card's DAPM locks -- so any path holding work_lock that calls into",
            "the codec closes a cycle (card -> work_lock -> DAPM), the same",
            "shape that already deadlocked the CeraLive vendor series, firing",
            "only when audio is present. Separately, hdmirx_plugout()'s",
            "cancel_delayed_work() does not wait for a running worker, and the",
            "worker unconditionally reschedules itself, so audio work kept",
            "polling and reporting present after every plugout.",
            "",
            "BEHAVIOUR. A synchronous cancel of delayed_work_audio is never",
            "performed under work_lock (enforced via",
            "lockdep_assert_not_held()); hook_plugged_cb() publishes the",
            "callback under the lock and invokes it with the lock dropped. An",
            "explicit armed gate replaces the ineffective async cancel: the",
            "worker checks it on entry and before re-arming, with a separate",
            "synchronous drain each caller makes after dropping work_lock.",
            "clk_set_rate() returns are now propagated instead of discarded, so",
            "a refused rate no longer updates audio_state as if it had taken.",
            "768000 is removed from supported_fs (CEA-861 tops out at 192 kHz;",
            "its only effect was letting a garbage ACR-derived frequency pass",
            "is_validfs()). audio_state's clock rate and audio_present move",
            "under a dedicated leaf lock, published before the codec callback",
            "rather than after.",
            "",
            "NON-GOALS. Does not add a synchronous cancel under work_lock --",
            "that path is exactly what the lock order forbids. Does not touch",
            "the audio FIFO/ACR sample-rate recovery logic 0005 owns.",
            "",
            "PROVENANCE. First-party CeraLive fix to the imported 0005 audio",
            "path; no upstream counterpart -- the PATCHv4 counterpart to 0005",
            "does not carry this audio worker at all.",
            "",
            "EVIDENCE POINTER. Source-verified and build-clean; hardware",
            "validation pending. Lock order enumerated from v7.1.7's own",
            "sound/soc/codecs/hdmi-codec.c. Two 0013-gated controls",
            "(delay_worker_ms, fail_clk_set_rate_once) force the races on",
            "demand; harness: tests/hdmirx-audio-fault-qa.sh under lockdep. See",
            "docs/BOARD-QUALIFICATION.md.",
        ),
    ),
    Patch(
        filename="0018-dma-buf-heaps-truthful-partial-registration.patch",
        ordinal=18,
        subject=(
            "dma-buf: heaps: report partial system-heap registration truthfully"
        ),
        provenance=NULL_OID,
        author="Andres Cera <andres.cera@hotmail.com>",
        date="Sun, 10 Aug 2026 14:00:00 -0500",
        origin=CERALIVE,
        rationale=(
            "MOTIVATION. 0009 added a second dma_heap_add() to",
            "system_heap_create(). If it fails, the \"system\" heap registered",
            "immediately before it is already live and cannot be withdrawn --",
            "dma_heap_add() has no counterpart at this base (no removal, no",
            "unregister, no atomic multi-add). The function returned the error",
            "and said nothing about the partial state, so nothing claims the",
            "pair is atomic in a comment nobody can check.",
            "v7.2 commit fd55edff8a0a modularizes the system heap but explicitly",
            "states that it cannot unload because the required infrastructure is",
            "still missing; modularization therefore does not provide rollback.",
            "",
            "BEHAVIOUR. States the behaviour instead of hiding it: the error",
            "message now names the partial state explicitly (first heap REMAINS",
            "REGISTERED and cannot be withdrawn), and the retire condition is",
            "written beside the function -- when the pinned base gains a real",
            "removal API, unwind on failure and assert the unwind instead of the",
            "retention. The registration sequence moves behind an internal",
            "add_fn seam so the failure path is reachable from a test at all.",
            "",
            "NON-GOALS. No atomicity is invented or claimed. No rollback is",
            "added -- the API cannot support one, and a fake cleanup that leaves",
            "the heap present while reporting removal would be worse than none.",
            "",
            "PROVENANCE. First-party CeraLive fix restructuring the registration",
            "0009 extends; no upstream counterpart -- mainline has no removal",
            "API to align with.",
            "",
            "EVIDENCE POINTER. KUnit-validated, boot path pending. All four",
            "cases of ceralive_system_heap_test (built under",
            "CONFIG_DMABUF_HEAPS_CERALIVE_TEST) PASS under qemu-system-aarch64",
            "on the applied series, including a non-vacuity case proving the",
            "injection seam is actually used; nothing real is registered by the",
            "suite. tests/check-kunit-heap.sh re-asserts the boot's actual heaps",
            "from userspace with an anchored TAP match.",
        ),
    ),
    Patch(
        filename="0026-hdmirx-register-lock-hardirq-context.patch",
        ordinal=26,
        subject=(
            "media: synopsys: hdmirx: make the register lock safe for "
            "its hardirq callers"
        ),
        provenance=NULL_OID,
        author="Andres Cera <andres.cera@hotmail.com>",
        date="Wed, 12 Aug 2026 01:10:00 -0500",
        origin=CERALIVE,
        rationale=(
            "MOTIVATION. A Rock 5B+ with a real HDMI source attached prints",
            "'BUG: Invalid wait context' out of the CEC hardirq before a",
            "shell exists: swapper/0/0 takes &hdmirx_dev->rst_lock",
            "{-.-.}-{3:3} at hdmirx_readl+0x2c in context-{2:2}, via",
            "hdmirx_cec_hardirq+0x8c and __handle_irq_event_percpu.",
            "spinlock_t is registered LD_WAIT_CONFIG, which is a sleeping",
            "rt_mutex under PREEMPT_RT; hardirq context is LD_WAIT_SPIN and",
            "may not wait on one. That is precisely the nesting",
            "CONFIG_PROVE_RAW_LOCK_NESTING exists to report.",
            "",
            "The report is worth more than the lock it names.",
            "print_lock_invalid_wait_context() calls debug_locks_off(), and",
            "lockdep never re-arms for the rest of that boot -- so every",
            "later 'possible recursive locking', 'bad unlock balance' and",
            "lock-order inversion in ANY subsystem goes unreported. It",
            "fires during probe, so on a board with a source attached there",
            "was no way to get a boot that had both live HDMI and live",
            "lockdep.",
            "",
            "CEC is not the only offender, merely the first to fire. The",
            "'hdmi' interrupt is requested with devm_request_irq() and NO",
            "threaded half, and hdmirx_hdmi_irq_handler() opens with twelve",
            "hdmirx_readl() calls before dispatching to sub-handlers that",
            "add more reads and writes. The DT declares that line",
            "IRQ_TYPE_LEVEL_HIGH, so its status registers must be read and",
            "acked in the primary handler or the line re-asserts forever.",
            "Deferring only the CEC read to a thread would therefore have",
            "moved the report to hdmirx_hdmi_irq_handler(), not removed it.",
            "",
            "BEHAVIOUR. rst_lock becomes a raw_spinlock_t and its four",
            "acquire sites become guard(raw_spinlock_irqsave). ONE lock",
            "still covers all of it: splitting a raw MMIO lock away from",
            "the reset would destroy the register-access-versus-DMA-reset",
            "exclusion the lock exists for, which is the whole reason it is",
            "called rst_lock. Nothing else changes -- same scope, same",
            "IRQ-save discipline, same leaf position, and on a non-RT build",
            "the emitted code is identical. What changes is that lockdep is",
            "now told the truth about a lock the driver has always taken",
            "from hardirq.",
            "",
            "That is only legal because nothing under it can sleep, which",
            "was checked at every site rather than assumed. Three of the",
            "four wrap readl()/writel() alone. The fourth,",
            "hdmirx_reset_dma(), calls reset_control_reset(), which",
            "drivers/reset/core.c does not annotate might_sleep() anywhere;",
            "its body is an SRCU read section -- legal in hardirq -- around",
            "rcdev->ops->reset. And on this SoC that op does not exist:",
            "rk3588-extra.dtsi points the hdmirx resets at &cru, whose",
            "rockchip_softrst_ops publishes only .assert and .deassert, so",
            "the call returns -ENOTSUPP before reaching a provider at all.",
            "",
            "NON-GOALS. Does not add a threaded half to the 'hdmi' or 'cec'",
            "interrupt, and does not move any register access out of",
            "hardirq -- both handlers need theirs where it is. Does not",
            "touch audio_lock or work_lock, which 0017 owns and which are",
            "taken only from process and workqueue context. Does not fix",
            "hdmirx_reset_dma() being a no-op on RK3588; that is a real",
            "upstream gap, it is unrelated to lock context, and it cannot",
            "be closed without a reset provider this SoC does not have.",
            "",
            "PROVENANCE. First-party CeraLive fix to imported code:",
            "rst_lock, its four accessors and both hardirq handlers are all",
            "v7.1.7's own, untouched by 0002/0003/0005/0006/0011/0012/0017.",
            "No upstream counterpart exists.",
            "",
            "EVIDENCE POINTER. Before/after on ONE Rock 5B+ with a physical",
            "HDMI source connected and locked, on the same lockdep kernel.",
            "Before: the trace above during probe, and /proc/lockdep_stats",
            "reading debug_locks: 0 by the time a shell exists. After: no",
            "Invalid wait context report, debug_locks: 1 after boot",
            "completes with the CEC interrupt confirmed to have fired, and",
            "HDMI-RX audio plus rkvenc encode unchanged. See",
            "docs/UPSTREAM-STATUS.md and docs/BOARD-QUALIFICATION.md.",
        ),
    ),
    Patch(
        filename="0027-hdmirx-phy-retry-hardening.patch",
        ordinal=27,
        subject=(
            "media: synopsys: hdmirx: stop trusting an SCDC bank the "
            "source never wrote"
        ),
        provenance=NULL_OID,
        author="Andres Cera <andres.cera@hotmail.com>",
        date="Thu, 13 Aug 2026 23:30:00 -0500",
        origin=CERALIVE,
        rationale=(
            "MOTIVATION. A Rock 5B+ will not lock a Sony FX3 sending",
            "3840x2160@59.94p over HDMI 2.0. tx_5v_power_present() reads 1",
            "and the receiver retries plugout/plugin forever, but across",
            "~500 consecutive link-setup attempts",
            "hdmirx_tmds_clk_ratio_config() logged scdc_regbank_st:0x0 and",
            "'HDMITX less than 3.4Gbps' every single time, with not one",
            "'greater than 3.4Gbps'. Four cables including a certified UHS",
            "48 Gbps one, camera power-cycles, board reboots and HPD/EDID",
            "re-apply cycles all change nothing, while 4K29.97p locks",
            "cleanly on the same physical chain -- so the camera, cable,",
            "EDID and receiver are each demonstrably capable.",
            "",
            "THE DEFECT. hdmirx_tmds_clk_ratio_config() derives the whole",
            "decision from one expression:",
            "",
            "  tmds_clk_ratio = (val & SCDC_TMDSBITCLKRATIO) > 0;",
            "",
            "An SCDC register bank the source never wrote reads 0. An",
            "explicit TMDS_Bit_Clock_Ratio = 1/10 declaration also reads 0.",
            "The function cannot tell 'the source told me 1/10' from 'the",
            "source has told me nothing at all', and it treats the empty",
            "bank as authoritative rather than as an absence of data -- it",
            "does not merely default to 1/10, it actively drives",
            "PHY_CONFIG.TMDS_CLOCK_RATIO = 0 into the PHY once per wait",
            "iteration and once more at the end of every",
            "hdmirx_phy_config(). Once a source has failed to write SCDC",
            "during the current HPD cycle, a >340 MHz link is therefore",
            "structurally unlockable for the rest of that cycle.",
            "",
            "That also explains why 0002's PHY re-init at i == 300 cannot",
            "recover this, and why raising the retry count or extending",
            "WAIT_SIGNAL_LOCK_TIME would not either: hdmirx_phy_config()",
            "is a genuine from-scratch PHY bring-up, but its LAST statement",
            "is hdmirx_tmds_clk_ratio_config(), so every retry ends by",
            "restoring precisely the configuration that cannot lock a",
            "scrambled 594 MHz link. Each further attempt consumes the same",
            "zero-valued input and reaches the same state.",
            "WAIT_SIGNAL_LOCK_TIME, NO_LOCK_CFG_RETRY_TIME and",
            "WAIT_LOCK_STABLE_TIME are left exactly as 0002 set them.",
            "",
            "BEHAVIOUR, part 1 -- say which condition actually failed. The",
            "wait loop tests three bits, and the failure path could not",
            "report on two of them. It printed SCDC_REGBANK_STATUS3, which",
            "is NOT the register the ratio is derived from -- naming the",
            "wrong register while claiming to explain a ratio decision --",
            "and it never printed cmu_st at all, even though the loop reads",
            "CMU_STATUS every iteration and TMDSQPCLK_LOCKED_ST is one of",
            "the three lock conditions. The defect above was consequently",
            "undiagnosable from the log alone. The failure path now also",
            "prints, at v4l2_err: cmu_st, SCDC_REGBANK_STATUS1,",
            "CMU_TMDSQPCLK_FREQ, PHY_CONFIG, PHY_STATUS, SCDC_CONFIG,",
            "DESCRAND_EN_CONTROL and DESCRAND_SYNC_SEQ_STATUS. Pure",
            "observability; no behaviour change, no new register",
            "definitions.",
            "",
            "It paid for itself immediately. On the failing board cmu_st",
            "reads 0x10000051 -- TMDSQPCLK_LOCKED_ST already SET, so the",
            "CMU had locked the whole time and only TMDSVALID_STABLE_ST and",
            "HDMIRX_LOCK were failing; regbank_st1 reads 0x0, confirming the",
            "empty bank on the register the ratio genuinely comes from;",
            "phy_cfg reads 0x8000, i.e. TMDS_CLOCK_RATIO clear, the PHY sat",
            "at 1/10; and CMU_TMDSQPCLK_FREQ reads 34753 kHz, x4 = 139.0",
            "MHz, which is why that counter is printed and NOT acted on -- a",
            "594 MHz 1/40 link mis-driven at 1/10 measures as an ordinary",
            "sub-340 MHz link, so gating recovery on it would silently never",
            "fire.",
            "",
            "BEHAVIOUR, part 2 -- one last-resort attempt at the other",
            "ratio. When, and only when, a full WAIT_SIGNAL_LOCK_TIME wait",
            "has already COMPLETED and failed, AND the derived ratio is",
            "still 0, AND +5V is still present, set a per-device",
            "tmds_clk_ratio_forced flag, re-run hdmirx_phy_config() -- which",
            "now brings the PHY up at 1/40 -- and re-enter the wait exactly",
            "once. The flag is cleared if that attempt also fails, and",
            "cleared in hdmirx_plugout(), so every new connection starts",
            "from the spec-compliant SCDC-derived value and a stale override",
            "cannot survive a replug.",
            "",
            "RISK. A link that locks never reaches the failure branch, so no",
            "working configuration can regress: the new code is unreachable",
            "until the compliant path has demonstrably failed. Worst case is",
            "a genuinely sub-340 MHz source failing for an unrelated reason",
            "spending one extra ~4.2 s wait before giving up.",
            "",
            "HONEST LABELLING. Part 1 is a bug fix -- the log named the",
            "wrong register and omitted a lock condition. Part 2 is a",
            "RECOVERY HEURISTIC, not spec-compliant behaviour, and is",
            "justified only because the compliant path has provably",
            "deadlocked by the time it runs.",
            "",
            "PROVENANCE. First-party CeraLive fix to imported code:",
            "hdmirx_tmds_clk_ratio_config(), hdmirx_wait_signal_lock() and",
            "hdmirx_plugout() are v7.1.7's own, as reworked by the imported",
            "0002 and 0026. No upstream counterpart exists, and none is",
            "claimed.",
            "",
            "EVIDENCE. Validated on REAL hardware -- a Radxa Rock 5B+ with a",
            "Sony FX3 at 3840x2160@59.94p, on a kernel differing from the",
            "failing one by this patch alone, with nothing physical touched",
            "between the two captures. 600/600 frames captured at 3840x2160,",
            "steady 59.94 fps, zero errors; reproduced 4/4 across",
            "independent HPD renegotiation cycles, including one live",
            "mid-session SCDC-drop recovery. Every cycle's first failure",
            "line reads forced:0, so the flag really is cleared per plug",
            "cycle and each cycle genuinely retries the compliant path",
            "first, and every lock is immediately preceded by this patch's",
            "own recovery message. NOT yet measured: a regression run",
            "against a source that DOES write SCDC. See",
            "docs/UPSTREAM-STATUS.md and docs/BOARD-QUALIFICATION.md.",
        ),
    ),
    Patch(
        filename="0028-rk3588-rock-5b-typec-dual-role-power.patch",
        ordinal=28,
        subject=(
            "arm64: dts: rockchip: rock 5b: advertise dual-role power in "
            "the Type-C PDOs"
        ),
        provenance=NULL_OID,
        author="Andres Cera <andres.cera@hotmail.com>",
        date="Thu, 27 Aug 2026 04:00:00 +0000",
        origin=CERALIVE,
        rationale=(
            "MOTIVATION. A live USB-PD diagnosis on a Rock 5B+ on 2026-08-27",
            "found that a requested power-role swap was rejected locally before",
            "the TCPM driver put any PR_SWAP traffic on the wire. Both of the",
            "Rock's fixed-supply capability records exposed",
            "dual_role_power=0 under usb_power_delivery/pd0, and that sysfs",
            "attribute is read-only. The board device tree advertises",
            "PDO_FIXED_USB_COMM on its fixed sink and source PDOs but omits",
            "PDO_FIXED_DUAL_ROLE, so no runtime policy can make the local TCPM",
            "port attempt the swap.",
            "",
            "The peer is not the missing-capability side: the Osmo Pocket 3's",
            "source capabilities were captured in the same live TCPM trace as",
            "[RUD]. tcpm_log_source_caps() decodes R as",
            "PDO_FIXED_DUAL_ROLE, U as PDO_FIXED_USB_COMM and D as",
            "PDO_FIXED_DATA_SWAP. The camera therefore already advertises the",
            "dual-role-power capability that the Rock's local fixed PDOs lack.",
            "",
            "BEHAVIOUR. OR PDO_FIXED_DUAL_ROLE into both fixed-supply PDOs for",
            "the Rock 5B+/5T Type-C connector. This declares the same",
            "power-role-swap capability while the board is a sink and while it",
            "is a source, allowing TCPM to send a PR_SWAP request instead of",
            "refusing it at the local capability gate. The variable sink PDO is",
            "unchanged.",
            "",
            "SCOPE. This is the narrow, owner-directed edge-track-only exception",
            "recorded at 2026-08-27T03:55Z and in the AMENDED 2026-08-27 Scope",
            "paragraph of the uvc-quirk-generalization plan. It applies only to",
            "the mainline v7.2 series and only to",
            "rk3588-rock-5b-5bp-5t.dtsi. The Orange Pi 5 Plus",
            "and the vendor 6.1 kernel track are explicitly outside this",
            "exception.",
            "",
            "NON-GOALS. Do not change power-role, try-power-role, data-role,",
            "connector status, the FUSB302 node status, voltage/current values,",
            "PDO_FIXED_DATA_SWAP or any other PDO flag. This declaration only",
            "permits a swap attempt; whether the camera accepts that request is a",
            "separate hardware result and is not claimed here.",
        ),
    ),
    Patch(
        filename="0029-rk3588-rock-5b-try-power-role-source.patch",
        ordinal=29,
        subject=(
            "arm64: dts: rockchip: rock 5b+: prefer the source power role "
            "on Type-C"
        ),
        provenance=NULL_OID,
        author="Andres Cera <andres.cera@hotmail.com>",
        date="Thu, 27 Aug 2026 15:00:00 +0000",
        origin=CERALIVE,
        rationale=(
            "MOTIVATION. A direct same-camera, same-policy A/B comparison on",
            "2026-08-27 isolated the remaining charging delta to the boards'",
            "Type-C preferred power role. The Rock 5B+ used its board-target",
            "try-power-role=\"sink\" override and showed MIXED, mostly absent",
            "charging, with repeated SNK_WAIT_CAPABILITIES_TIMEOUT while waiting",
            "for source capabilities. The Orange Pi 5 Plus used its own existing",
            "source preference and charged immediately and reliably on first",
            "attach; its policy journal recorded \"settled as power_role=source",
            "data_role=host -- no data-role swap needed\".",
            "",
            "Ground truth was re-read from the pinned v7.2 tree before writing",
            "this patch. The shared rk3588-rock-5b-5bp-5t.dtsi defines usb_con",
            "and its PDOs, but the Rock 5B+ target file",
            "rk3588-rock-5b-plus.dts overrides that labelled connector with",
            "power-role=\"dual\" and try-power-role=\"sink\". This patch changes",
            "the existing board-target override; it does not add a new property",
            "to the shared connector node.",
            "",
            "BEHAVIOUR. Change only the Rock 5B+ connector's try-power-role value",
            "from sink to source. The port remains dual-role, but TCPM starts its",
            "normal dual-role toggling with a Try.SRC preference so a compatible",
            "attach can naturally settle as source/host and supply the camera.",
            "",
            "SCOPE. This is the narrow, owner-directed edge-track-only exception",
            "recorded by todo 29 and the 2026-08-27 amendment to the Scope section",
            "of the uvc-quirk-generalization plan. It applies only to the mainline",
            "v7.2 series and the Rock 5B+ board-target override in",
            "rk3588-rock-5b-plus.dts. The Rock 5B, Rock 5T, Orange Pi 5 Plus and",
            "vendor 6.1 kernel track are outside this amendment.",
            "",
            "NON-GOALS. try-power-role is a soft USB Type-C preference: Try.SRC",
            "still completes the normal CC-toggle detection handshake and leaves",
            "the port capable of either power role. It is not FORCE_SOURCE, the",
            "hard port_type=source pin that skips that handshake and was already",
            "proven to break camera attachment in 3/3 physical replicates. Do not",
            "change port_type, power-role, data-role, connector or FUSB302 status,",
            "the PDO declarations added by 0028, or any Orange Pi property.",
            "",
            "This patch does not claim charging reliability is fixed. Todo 30's",
            "separate, not-yet-run multi-cycle hardware test determines whether",
            "the preference is reliable; this change proves only that the intended",
            "one-line DTS amendment applies cleanly to the pinned edge tree.",
        ),
    ),
    Patch(
        filename="0030-rk3588-orangepi-5-plus-typec-dual-role-power.patch",
        ordinal=30,
        subject=(
            "arm64: dts: rockchip: orange pi 5 plus: advertise dual-role power "
            "in the Type-C PDOs"
        ),
        provenance=NULL_OID,
        author="Andres Cera <andres.cera@hotmail.com>",
        date="Thu, 27 Aug 2026 16:00:00 +0000",
        origin=CERALIVE,
        rationale=(
            "MOTIVATION. A live readback on an Orange Pi 5 Plus on 2026-08-27",
            "found dual_role_power=0 on both source-capabilities and",
            "sink-capabilities below the FUSB302 port's usb_power_delivery/pd0",
            "directory at i2c-6/6-0022. The operator independently recalled the",
            "same connection-capability issue occurring on this board before.",
            "The Rock 5B+ showed the same gap at i2c-4/4-0022 before 0028.",
            "Both boards use the identical fusb302 / fcs,fusb302 controller at",
            "address 0x22, so the live result identifies capability parity as",
            "missing on the Orange Pi rather than a different controller policy.",
            "",
            "Ground truth was independently re-read from the exact pinned v7.2",
            "commit before writing this patch. The Orange Pi's own board file,",
            "rk3588-orangepi-5-plus.dts, defines usb-typec@22 under i2c6 and its",
            "connector inline. Its fixed source PDO is 5000 mV / 1400 mA and its",
            "fixed sink PDO is 5000 mV / 10 mA; both carry only",
            "PDO_FIXED_USB_COMM. Neither declaration has PDO_FIXED_DUAL_ROLE.",
            "",
            "BEHAVIOUR. OR PDO_FIXED_DUAL_ROLE into both existing fixed-supply",
            "PDOs for the Orange Pi 5 Plus Type-C connector. This advertises the",
            "same dual-role-power capability while the board is a source and while",
            "it is a sink. The board's own voltage and current values are preserved.",
            "",
            "SCOPE. This is the owner-directed edge-track-only exception recorded",
            "by todo 32 and the 2026-08-27 amendment to the",
            "uvc-quirk-generalization plan. It applies only to the mainline v7.2",
            "series and rk3588-orangepi-5-plus.dts. Patch 0028 and every Rock",
            "5B/5B+/5T file remain byte-unchanged; the vendor 6.1 track is outside",
            "this amendment.",
            "",
            "NON-GOALS. This patch does not claim PR_SWAP now works on the Orange",
            "Pi. Todo 21's adaptive policy never attempts PR_SWAP on any board:",
            "that path is gated behind TYPEC_PRSWAP: ACCEPTED, which has never been",
            "recorded for either board. This is a capability-parity fix with no",
            "immediately exercised behaviour change. Do not change try-power-role,",
            "power-role, data-role, connector or FUSB302 status, voltage/current",
            "values, or any other PDO flag on the Orange Pi.",
        ),
    ),
    Patch(
        filename="0031-rk3588-media-island-drivers.patch",
        ordinal=31,
        subject=(
            "video: rockchip: add the CeraLive RK3588 media island"
        ),
        provenance=Island(
            tag="v2026.9.2",
            commit="1fd357d8a8b83b6f4ed7f7692d761f7b653d44f5",
            asset_sha256=(
                "393b50a26117b95659f35a603abb9939f767e397f71e85fb180dda107e2df616"
            ),
        ),
        author="CeraLive <dev@ceralive.tv>",
        date="Wed, 2 Sep 2026 00:00:00 +0000",
        origin=ISLAND,
    ),
    Patch(
        filename="0032-video-rockchip-kconfig-makefile-hooks.patch",
        ordinal=32,
        subject=(
            "video: rockchip: hook the MPP and multi_rga Kconfig and Makefiles"
        ),
        provenance=Island(
            tag="v2026.9.2",
            commit="1fd357d8a8b83b6f4ed7f7692d761f7b653d44f5",
            asset_sha256=(
                "393b50a26117b95659f35a603abb9939f767e397f71e85fb180dda107e2df616"
            ),
        ),
        author="CeraLive <dev@ceralive.tv>",
        date="Wed, 2 Sep 2026 00:00:00 +0000",
        origin=ISLAND,
    ),
    Patch(
        filename="0033-iommu-rockchip-export-for-mpp.patch",
        ordinal=33,
        subject=(
            "iommu: rockchip: export media-provider control for MPP and RGA"
        ),
        provenance=Island(
            tag="v2026.9.2",
            commit="1fd357d8a8b83b6f4ed7f7692d761f7b653d44f5",
            asset_sha256=(
                "393b50a26117b95659f35a603abb9939f767e397f71e85fb180dda107e2df616"
            ),
        ),
        author="CeraLive <dev@ceralive.tv>",
        date="Wed, 2 Sep 2026 00:00:00 +0000",
        origin=ISLAND,
    ),
    Patch(
        filename="0034-iommu-dma-expose-iova-domain.patch",
        ordinal=34,
        subject=(
            "iommu: expose media IOVA allocation helpers"
        ),
        provenance=Island(
            tag="v2026.9.2",
            commit="1fd357d8a8b83b6f4ed7f7692d761f7b653d44f5",
            asset_sha256=(
                "393b50a26117b95659f35a603abb9939f767e397f71e85fb180dda107e2df616"
            ),
        ),
        author="CeraLive <dev@ceralive.tv>",
        date="Wed, 2 Sep 2026 00:00:00 +0000",
        origin=ISLAND,
    ),
    Patch(
        filename="0035-arm64-dts-rk3588-mpp-encoder-nodes.patch",
        ordinal=35,
        subject=(
            "arm64: dts: rockchip: add RK3588 MPP encoder nodes"
        ),
        provenance=Island(
            tag="v2026.9.2",
            commit="1fd357d8a8b83b6f4ed7f7692d761f7b653d44f5",
            asset_sha256=(
                "393b50a26117b95659f35a603abb9939f767e397f71e85fb180dda107e2df616"
            ),
        ),
        author="CeraLive <dev@ceralive.tv>",
        date="Wed, 2 Sep 2026 00:00:00 +0000",
        origin=ISLAND,
    ),
    Patch(
        filename="0036-arm64-dts-rk3588-mpp-decoder-nodes.patch",
        ordinal=36,
        subject=(
            "arm64: dts: rockchip: hand RK3588 decoders to MPP"
        ),
        provenance=Island(
            tag="v2026.9.2",
            commit="1fd357d8a8b83b6f4ed7f7692d761f7b653d44f5",
            asset_sha256=(
                "393b50a26117b95659f35a603abb9939f767e397f71e85fb180dda107e2df616"
            ),
        ),
        author="CeraLive <dev@ceralive.tv>",
        date="Wed, 2 Sep 2026 00:00:00 +0000",
        origin=ISLAND,
    ),
    Patch(
        filename="0037-arm64-dts-rk3588-mpp-jpegd-node.patch",
        ordinal=37,
        subject=(
            "arm64: dts: rockchip: add the RK3588 MPP JPEG decoder"
        ),
        provenance=Island(
            tag="v2026.9.2",
            commit="1fd357d8a8b83b6f4ed7f7692d761f7b653d44f5",
            asset_sha256=(
                "393b50a26117b95659f35a603abb9939f767e397f71e85fb180dda107e2df616"
            ),
        ),
        author="CeraLive <dev@ceralive.tv>",
        date="Wed, 2 Sep 2026 00:00:00 +0000",
        origin=ISLAND,
    ),
    Patch(
        filename="0038-arm64-dts-rk3588-rga3-vendor-compat.patch",
        ordinal=38,
        subject="arm64: dts: rockchip: give RK3588 RGA3 ownership to multi_rga",
        provenance=Island(
            tag="v2026.9.2",
            commit="1fd357d8a8b83b6f4ed7f7692d761f7b653d44f5",
            asset_sha256=(
                "393b50a26117b95659f35a603abb9939f767e397f71e85fb180dda107e2df616"
            ),
        ),
        author="CeraLive <dev@ceralive.tv>",
        date="Wed, 2 Sep 2026 00:00:00 +0000",
        origin=ISLAND,
    ),
    Patch(
        filename="0039-arm64-dts-rk3588-rga2-vendor-compat.patch",
        ordinal=39,
        subject="arm64: dts: rockchip: give RK3588 RGA2 ownership to multi_rga",
        provenance=Island(
            tag="v2026.9.2",
            commit="1fd357d8a8b83b6f4ed7f7692d761f7b653d44f5",
            asset_sha256=(
                "393b50a26117b95659f35a603abb9939f767e397f71e85fb180dda107e2df616"
            ),
        ),
        author="CeraLive <dev@ceralive.tv>",
        date="Wed, 2 Sep 2026 00:00:00 +0000",
        origin=ISLAND,
    ),
    Patch(
        filename="0040-hdmirx-refuse-edid-while-streaming.patch",
        ordinal=40,
        subject="media: synopsys: hdmirx: refuse S_EDID while streaming",
        provenance=NULL_OID,
        author="Andres Cera <andres.cera@hotmail.com>",
        date="Sat, 5 Sep 2026 12:00:00 +0000",
        origin=CERALIVE,
        rationale=(
            "EDID writes trigger HPD renegotiation and controller teardown.",
            "Reject them before any state or hardware mutation while the capture",
            "queue is streaming, including zero-block requests that clear EDID.",
            "Both vdev->lock and the vb2 queue lock use stream->vlock, so the",
            "check and write are serialized with STREAMON and STREAMOFF.",
            "Idle writes retain the existing validation and renegotiation path.",
            "Intended for upstream submission; retire when the base absorbs it.",
        ),
    ),
)


class SeriesError(RuntimeError):
    """Anything this converter refuses to guess its way past."""


class RebaseError(SeriesError):
    """A rule could not be applied safely. Never resolved silently."""


class PinError(SeriesError):
    """kernel-pin.env does not parse the way bash would read it."""


class LaneError(SeriesError):
    """A source file is not accounted for exactly once."""


ASSIGNMENT_RE = re.compile(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def parse_pin_value(rhs: str, where: str) -> str:
    """Read one right-hand side of KEY=... the way bash sources it.

    kernel-pin.env annotates most pins with a trailing ``# what this is`` comment.
    Stripping quotes alone leaves that comment glued to the value, which then gets
    written verbatim into generated metadata -- patches/series carried
    ``155b42be..."          # v7.1.5^{commit}`` for exactly that reason.
    """
    rest = rhs.lstrip()
    if not rest or rest.startswith("#"):
        return ""

    if rest[0] in ("'", '"'):
        quote = rest[0]
        end = rest.find(quote, 1)
        if end == -1:
            raise PinError(f"{where}: unterminated {quote} in value")
        value, trailer = rest[1:end], rest[end + 1 :]
    else:
        # Unquoted: bash ends the word at whitespace, and only treats '#' as a
        # comment when it STARTS a word -- so FOO=bar#baz really is "bar#baz".
        value = rest.split(maxsplit=1)[0]
        trailer = rest[len(value) :]

    trailer = trailer.strip()
    if trailer and not trailer.startswith("#"):
        raise PinError(f"{where}: unparsed text after the value: {trailer!r}")
    return value


def read_pin() -> dict[str, str]:
    """Parse the shell-ish kernel-pin.env into a plain dict."""
    pin: dict[str, str] = {}
    for lineno, raw in enumerate(PIN_FILE.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = ASSIGNMENT_RE.match(line)
        if not match:
            continue
        key, rhs = match.groups()
        pin[key] = parse_pin_value(rhs, f"{PIN_FILE.name}:{lineno}")
    return pin


@dataclass(frozen=True)
class Retired:
    filename: str
    lane: str
    ordinal: int | None  # None only for a lane that holds no series slot
    retired: str
    kernel_tag: str
    reason: str
    lineno: int


def load_retired() -> dict[str, Retired]:
    """Parse the retirement registry table out of retired/REGISTRY.md.

    A Markdown table, because the repo already parses '|'-delimited state files
    (rebase/*.rules) and a table is the one format that is both the doc and the
    machine input -- there is no second copy to drift.
    """
    if not REGISTRY_FILE.is_file():
        raise LaneError(f"missing retirement registry: {REGISTRY_FILE}")

    # Anchor on the header row and take only its contiguous run, so the file is
    # free to carry other Markdown tables (the column legend) around it.
    rows: list[tuple[int, list[str]]] = []
    started = False
    for lineno, raw in enumerate(
        REGISTRY_FILE.read_text(encoding="utf-8").splitlines(), 1
    ):
        line = raw.strip()
        if not line.startswith("|"):
            if started:
                break
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not started:
            if tuple(cells) != REGISTRY_COLUMNS:
                continue
            started = True
        rows.append((lineno, cells))

    if len(rows) < 2:
        raise LaneError(
            f"{REGISTRY_FILE.name}: expected a table headed {REGISTRY_COLUMNS} with "
            "its ---- rule. Both rows are mandatory even when nothing is retired -- "
            "they are the shape the parser validates against"
        )

    rule_lineno, rule = rows[1]
    if not all(REGISTRY_RULE_RE.match(c) for c in rule):
        raise LaneError(f"{REGISTRY_FILE.name}:{rule_lineno}: expected the ---- rule")

    entries: dict[str, Retired] = {}
    for lineno, cells in rows[2:]:
        if len(cells) != len(REGISTRY_COLUMNS):
            raise LaneError(
                f"{REGISTRY_FILE.name}:{lineno}: {len(cells)} cells, "
                f"expected {len(REGISTRY_COLUMNS)}"
            )
        name, lane, ordinal, retired, tag, reason = (c.strip("`") for c in cells)
        if lane not in RETIRABLE_LANES:
            raise LaneError(
                f"{REGISTRY_FILE.name}:{lineno}: lane {lane!r} is not one of "
                f"{sorted(RETIRABLE_LANES)}"
            )
        if lane in SOURCE_DIRS:
            if not ordinal.isdigit():
                raise LaneError(
                    f"{REGISTRY_FILE.name}:{lineno}: ordinal {ordinal!r} is not a "
                    "number, and a source-lane retirement always held a slot"
                )
        elif ordinal != NO_ORDINAL:
            raise LaneError(
                f"{REGISTRY_FILE.name}:{lineno}: {lane}/ holds no series slot, so "
                f"its ordinal must be {NO_ORDINAL!r}, not {ordinal!r}"
            )
        if not (retired and tag and reason):
            raise LaneError(
                f"{REGISTRY_FILE.name}:{lineno}: Retired, Kernel tag and Reason "
                "are all mandatory -- a retirement with no recorded why is a deletion"
            )
        if name in entries:
            raise LaneError(
                f"{REGISTRY_FILE.name}:{lineno}: {name} is registered twice "
                f"(first at line {entries[name].lineno})"
            )
        entries[name] = Retired(
            filename=name,
            lane=lane,
            ordinal=int(ordinal) if ordinal.isdigit() else None,
            retired=retired,
            kernel_tag=tag,
            reason=reason,
            lineno=lineno,
        )
    return entries


def validate_series() -> list[str]:
    """Per-entry lane invariants: what each lane obliges a SERIES member to carry."""
    problems: list[str] = []
    for patch in SERIES:
        where = f"SERIES entry {patch.filename}"
        if patch.origin not in SOURCE_DIRS:
            problems.append(f"{where}: unknown origin {patch.origin!r}")
            continue
        if patch.ordinal > SERIES_TOTAL:
            problems.append(
                f"{where}: ordinal {patch.ordinal} exceeds SERIES_TOTAL "
                f"{SERIES_TOTAL}, so the N/{SERIES_TOTAL} subject would lie"
            )
        if patch.origin == BACKPORTS:
            problems += validate_backports_entry(patch, where)
        elif patch.origin == ISLAND:
            problems += validate_island_entry(patch, where)
        else:
            if patch.backport is not None:
                problems.append(
                    f"{where}: only the {BACKPORTS}/ lane carries a Backport"
                )
            if patch.lore is not None:
                problems.append(
                    f"{where}: only the {BACKPORTS}/ lane carries a LorePosting"
                )
            if isinstance(patch.provenance, Island):
                problems.append(f"{where}: only the {ISLAND}/ lane carries an Island")
        if patch.origin == CERALIVE and not patch.rationale:
            problems.append(f"{where}: a first-party patch must state why it exists")
    problems += validate_one_island_release()
    return problems


def validate_one_island_release() -> list[str]:
    """The lane mirrors ONE release, so a half-finished import is loud.

    Seven members naming two releases would still pass every per-entry check and
    would still generate; what it would mean is that somebody updated part of the
    lane. The digest gate cannot see that, because each member would verify
    against the asset it names.
    """
    releases = {
        (p.provenance.tag, p.provenance.commit, p.provenance.asset_sha256)
        for p in SERIES
        if p.origin == ISLAND and isinstance(p.provenance, Island)
    }
    if len(releases) <= 1:
        return []
    named = ", ".join(sorted(f"rk3588-media-island@{tag}" for tag, _, _ in releases))
    return [
        f"the {ISLAND}/ lane names more than one island release ({named}); the lane "
        "mirrors one release at a time, so a partial re-import is a stop"
    ]


def validate_island_entry(patch: Patch, where: str) -> list[str]:
    """The island lane names a RELEASE, never a commit, and never a second variant."""
    problems: list[str] = []
    if patch.backport is not None or patch.lore is not None:
        problems.append(
            f"{where}: an island member is generated by the island's own release "
            "workflow; carrying a Backport or LorePosting beside it claims two "
            "mutually exclusive origins"
        )
        return problems
    if not isinstance(patch.provenance, Island):
        problems.append(
            f"{where}: the {ISLAND}/ lane must name the release it was generated "
            "from as provenance=Island(tag=..., commit=..., asset_sha256=...). "
            "A string or mixed Island/string value claims a kernel identity too"
        )
        return problems

    island = patch.provenance
    for name, value in (
        ("tag", island.tag),
        ("commit", island.commit),
        ("asset_sha256", island.asset_sha256),
    ):
        if not value.strip():
            problems.append(f"{where}: Island.{name} is mandatory and empty")
    if island.commit and not SHA1_RE.match(island.commit):
        problems.append(
            f"{where}: Island.commit is not a 40-hex object id: {island.commit!r}"
        )
    if island.asset_sha256 and not SHA256_RE.match(island.asset_sha256):
        problems.append(f"{where}: Island.asset_sha256 is not a sha256 digest")
    if island.tag and not ISLAND_TAG_RE.match(island.tag):
        problems.append(
            f"{where}: Island.tag {island.tag!r} is not a vYYYY.M.P release tag"
        )
    problems += validate_island_mailbox(patch, where)
    return problems


def validate_island_mailbox(patch: Patch, where: str) -> list[str]:
    """The declared identity has to be the mailbox's own, or one of them is wrong.

    Nothing here rewrites the member -- it is byte-preserved. The point is that the
    SERIES entry restates the member's subject, author and date so they can appear
    in a generated header, and a restatement that drifts from the bytes it claims
    to describe is exactly the silent kind of wrong this repository refuses.
    """
    source = SOURCE_DIRS[ISLAND] / patch.filename
    if not source.is_file():
        return [f"{where}: {ISLAND}/{patch.filename} does not exist"]

    headers = mailbox_headers(source.read_text(encoding="utf-8", errors="surrogateescape"))
    problems: list[str] = []
    subject = headers.get("Subject", "")
    stripped = re.sub(r"^\[PATCH[^]]*\]\s*", "", subject)
    if stripped != patch.subject:
        problems.append(
            f"{where}: declares subject {patch.subject!r}, but the member's own "
            f"Subject is {stripped!r}"
        )
    if headers.get("From", "") != patch.author:
        problems.append(
            f"{where}: declares author {patch.author!r}, but the member's own "
            f"From is {headers.get('From', '')!r}"
        )
    if headers.get("Date", "") != patch.date:
        problems.append(
            f"{where}: declares date {patch.date!r}, but the member's own "
            f"Date is {headers.get('Date', '')!r}"
        )

    member = island_member_name(patch)
    if patch.filename.split("-", 1)[1:] != member.split("-", 1)[1:]:
        problems.append(
            f"{where}: {ISLAND}/{patch.filename} and asset member {member} do not "
            "share a stem, so the ordinal re-prefix is not mechanical"
        )
    return problems


def island_member_name(patch: Patch) -> str:
    """Map this repository's continuing ordinal to the release's 1-based ordinal."""
    _, separator, stem = patch.filename.partition("-")
    if not separator:
        raise LaneError(f"{patch.filename}: island member filename has no ordinal")
    return f"{patch.ordinal - ISLAND_ORDINAL_OFFSET:04d}-{stem}"


def mailbox_headers(text: str) -> dict[str, str]:
    """The RFC822 headers of a mailbox member, up to its first blank line."""
    headers: dict[str, str] = {}
    for line in text.splitlines():
        if not line:
            break
        key, _, value = line.partition(": ")
        if value:
            headers[key] = value
    return headers


def validate_backports_entry(patch: Patch, where: str) -> list[str]:
    """The backports lane has exactly two provenance variants, never both."""
    problems: list[str] = []
    if isinstance(patch.provenance, Island):
        return [f"{where}: only the {ISLAND}/ lane carries an Island"]
    if patch.backport is not None and patch.lore is not None:
        problems.append(
            f"{where}: a backport is EITHER a merged commit OR an unmerged lore "
            "posting; carrying both provenance variants at once claims two "
            "mutually exclusive origins"
        )
        return problems
    if patch.backport is None and patch.lore is None:
        problems.append(
            f"{where}: the {BACKPORTS}/ lane must name its own origin; give it a "
            "Backport(upstream_subject=..., lore_msgid=...) for a merged commit, "
            "or a LorePosting(...) for an unmerged posting"
        )
        return problems

    if patch.backport is not None:
        # NULL_OID is 40 hex digits, so the shape test alone would let a
        # provenance-less backport through -- and "no originating commit" is
        # the one thing a merged-commit backport cannot be.
        if patch.provenance == NULL_OID or not SHA1_RE.match(patch.provenance):
            problems.append(
                f"{where}: a backport's provenance must be the 40-hex commit "
                f"it is backported from, not {patch.provenance!r}"
            )
        return problems

    lore = patch.lore
    assert lore is not None
    if patch.provenance != LORE_POSTING:
        problems.append(
            f"{where}: an unmerged posting has no commit id, so its provenance "
            f"must be exactly {LORE_POSTING!r}, not {patch.provenance!r}. A 40-hex "
            "value here -- NULL_OID, a parent, or any other -- asserts an identity "
            "that does not exist"
        )
    required = {
        "lore_msgid": lore.lore_msgid,
        "revision": lore.revision,
        "posted_date": lore.posted_date,
        "upstream_subject": lore.upstream_subject,
        "thread_compressed_sha256": lore.thread_compressed_sha256,
        "thread_mbox_sha256": lore.thread_mbox_sha256,
        "canonical_patch_sha256": lore.canonical_patch_sha256,
        "canonical_mail": lore.canonical_mail,
        "review_state": lore.review_state,
    }
    for name, value in required.items():
        if not value.strip():
            problems.append(f"{where}: LorePosting.{name} is mandatory and empty")
    if not lore.note:
        problems.append(f"{where}: LorePosting.note is mandatory and empty")
    if lore.revision and not REVISION_RE.match(lore.revision):
        problems.append(
            f"{where}: LorePosting.revision {lore.revision!r} is not a vN revision"
        )
    if lore.thread_compressed_sha256 == lore.thread_mbox_sha256:
        problems.append(
            f"{where}: thread_compressed_sha256 equals thread_mbox_sha256; those "
            "are different domains (the .gz response vs the mailbox it expands to) "
            "and one of them was computed over the wrong bytes"
        )
    for name in (
        "thread_compressed_sha256",
        "thread_mbox_sha256",
        "canonical_patch_sha256",
    ):
        value = required[name]
        if value and not SHA256_RE.match(value):
            problems.append(f"{where}: LorePosting.{name} is not a sha256 digest")
    mail = ROOT / lore.canonical_mail
    if lore.canonical_mail and not mail.is_file():
        problems.append(
            f"{where}: LorePosting.canonical_mail {lore.canonical_mail} is missing; "
            "the archived canonical mail is what makes canonical_patch_sha256 "
            "recomputable without the network"
        )
    elif lore.canonical_patch_sha256:
        actual = hashlib.sha256(mail.read_bytes()).hexdigest()
        if actual != lore.canonical_patch_sha256:
            problems.append(
                f"{where}: {lore.canonical_mail} hashes to {actual}, but "
                f"canonical_patch_sha256 records {lore.canonical_patch_sha256}"
            )
    return problems


def check_membership(retired: dict[str, Retired]) -> None:
    """Every source-lane patch is active OR retired -- exactly once, never neither.

    This is the check that makes a forgotten file loud. Dropping a patch into
    upstream/ or backports/ without a SERIES entry used to be a silent no-op: the
    converter walked its hard-coded list and never looked at the directory.
    """
    problems: list[str] = []

    active: dict[str, Patch] = {}
    ordinals: dict[int, str] = {}
    for patch in SERIES:
        if patch.filename in active:
            problems.append(
                f"SERIES lists {patch.filename} more than once; membership is "
                "exactly once"
            )
            continue
        active[patch.filename] = patch
        if patch.ordinal in ordinals:
            problems.append(
                f"ordinal {patch.ordinal} is claimed by both "
                f"{ordinals[patch.ordinal]} and {patch.filename}"
            )
        ordinals[patch.ordinal] = patch.filename

    for patch in active.values():
        src = SOURCE_DIRS[patch.origin] / patch.filename
        if not src.is_file():
            problems.append(
                f"{patch.filename} is in SERIES as {patch.origin}/ but "
                f"{patch.origin}/{patch.filename} does not exist"
            )
        duplicated = [
            lane
            for lane, directory in SOURCE_DIRS.items()
            if lane != patch.origin and (directory / patch.filename).is_file()
        ]
        if duplicated:
            problems.append(
                f"{patch.filename} exists in {patch.origin}/ and also in "
                f"{', '.join(sorted(duplicated))}/; provenance must be unambiguous"
            )

    for lane, directory in SOURCE_DIRS.items():
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob(LANE_GLOB)):
            if path.name in active:
                continue
            if path.name in retired:
                problems.append(
                    f"{lane}/{path.name} is registered as retired but still sits in "
                    f"{lane}/; retirement MOVES the file into retired/"
                )
                continue
            problems.append(
                f"orphan source: {lane}/{path.name} is in no SERIES entry and no "
                "retirement registry row. Add it to SERIES in "
                "scripts/build-series.py, or retire it per retired/REGISTRY.md"
            )

    # Every file, not just *.patch: overlays/ retires a .dts, and an archived
    # artifact of any suffix with no registry row is an unexplained archive.
    archived = (
        {
            p.name
            for p in RETIRED_DIR.iterdir()
            if p.is_file() and p.name != REGISTRY_FILE.name
        }
        if RETIRED_DIR.is_dir()
        else set()
    )
    for name in sorted(archived - set(retired)):
        problems.append(
            f"retired/{name} is archived but has no row in {REGISTRY_FILE.name}"
        )
    for name, entry in sorted(retired.items()):
        if name not in archived:
            problems.append(
                f"{REGISTRY_FILE.name}:{entry.lineno} retires {name} but "
                f"retired/{name} is missing; retiring MOVES the file, and deleting "
                "a source file is never legal"
            )
        if name in active:
            problems.append(
                f"{name} is both an active SERIES member and retired at "
                f"{REGISTRY_FILE.name}:{entry.lineno}; it must be exactly one"
            )
        origin = RETIRABLE_LANES[entry.lane]
        if entry.lane not in SOURCE_DIRS and (origin / name).is_file():
            problems.append(
                f"{entry.lane}/{name} is registered as retired but still sits in "
                f"{entry.lane}/; retirement MOVES the file into retired/"
            )
        if entry.ordinal is None:
            continue
        holder = ordinals.get(entry.ordinal)
        if holder and holder != name:
            problems.append(
                f"ordinal {entry.ordinal} was retired with {name} but is reused by "
                f"{holder}; slots are never renumbered or reused"
            )

    problems += validate_series()

    if problems:
        raise LaneError(
            "source lanes are not accounted for:\n  - " + "\n  - ".join(problems)
        )


@dataclass(frozen=True)
class Rule:
    patch: str
    op: str
    anchor: str
    payload: str
    lineno: int


def load_rules(tag: str) -> list[Rule]:
    """Load rebase/<tag>.rules. Absent file means the series needs no re-anchoring."""
    path = REBASE_DIR / f"{tag}.rules"
    if not path.exists():
        return []

    rules: list[Rule] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split("|")
        if len(fields) != 4:
            raise RebaseError(f"{path}:{lineno}: expected 4 '|'-separated fields")
        patch, op, anchor, payload = fields
        if op not in {"replace", "insert-before"}:
            raise RebaseError(f"{path}:{lineno}: unknown op {op!r}")
        rules.append(
            Rule(
                patch=patch,
                op=op,
                # Rules are written with literal \t for readability.
                anchor=anchor.replace("\\t", "\t"),
                payload=payload.replace("\\t", "\t"),
                lineno=lineno,
            )
        )
    return rules


def _hunk_bounds(lines: list[str], idx: int) -> tuple[int, int]:
    """Return [start, end) of the hunk body containing body-line index `idx`."""
    start = idx
    while start >= 0 and not HUNK_RE.match(lines[start]):
        start -= 1
    if start < 0:
        raise RebaseError("matched line is not inside a hunk")
    end = start + 1
    while end < len(lines) and not (
        HUNK_RE.match(lines[end])
        or lines[end].startswith("diff -ruN ")
        or lines[end].startswith("--- ")
        or lines[end].startswith("+++ ")
    ):
        end += 1
    return start, end


def _bump_hunk_header(header: str, delta: int) -> str:
    """Widen a @@ header's old and new counts by `delta`."""
    m = HUNK_RE.match(header)
    if not m:
        raise RebaseError(f"not a hunk header: {header!r}")
    old_start, old_len, new_start, new_len, trailer = m.groups()
    old_count = int(old_len) if old_len is not None else 1
    new_count = int(new_len) if new_len is not None else 1
    return (
        f"@@ -{old_start},{old_count + delta} "
        f"+{new_start},{new_count + delta} @@{trailer}"
    )


def apply_rule(lines: list[str], rule: Rule) -> list[str]:
    """Apply one context-only rule. Raises rather than guessing."""
    target = " " + rule.anchor  # context lines carry a leading space in a diff
    hits = [i for i, line in enumerate(lines) if line == target]

    if not hits:
        # Also look for the anchor as a '+'/'-' line, to give a precise diagnosis
        # instead of a bare "not found".
        for i, line in enumerate(lines):
            if line[1:] == rule.anchor and line[:1] in ("+", "-"):
                raise RebaseError(
                    f"rule at rebase line {rule.lineno} matched a "
                    f"{'added' if line[0] == '+' else 'removed'} line, not context. "
                    "Rules may only re-anchor context; this would change behaviour."
                )
        raise RebaseError(
            f"rule at rebase line {rule.lineno}: anchor not found in {rule.patch}"
        )
    if len(hits) > 1:
        raise RebaseError(
            f"rule at rebase line {rule.lineno}: anchor matched {len(hits)} times "
            f"in {rule.patch}; it must be unambiguous"
        )

    idx = hits[0]
    out = list(lines)

    if rule.op == "replace":
        out[idx] = " " + rule.payload
        return out

    # insert-before: one extra context line widens both sides of the hunk by 1.
    hunk_start, _ = _hunk_bounds(out, idx)
    out.insert(idx, " " + rule.payload)
    out[hunk_start] = _bump_hunk_header(out[hunk_start], 1)
    return out


def source_path(patch: Patch) -> Path:
    return SOURCE_DIRS[patch.origin] / patch.filename


def split_mailbox(lines: list[str]) -> tuple[list[str], list[str]]:
    """(message body, diff) of an already-generated mailbox member.

    The RFC822 headers are dropped: this repository restates From/Date/Subject
    itself so the N/SERIES_TOTAL ordinal is ours. Everything between them and the
    bare '---' is the member's own message, which carries its Origin: trailers and
    is therefore provenance, not decoration -- it is reproduced verbatim.
    """
    try:
        end = lines.index("---")
    except ValueError as exc:
        raise RebaseError(
            "island member has no '---' separator, so it is not a mailbox"
        ) from exc
    try:
        blank = lines.index("")
    except ValueError as exc:
        raise RebaseError("island member has no header/body separator") from exc
    if blank > end:
        raise RebaseError("island member's headers run past its '---' separator")
    return lines[blank + 1 : end], lines[end + 1 :]


def build_patch(patch: Patch, rules: list[Rule], pin: dict[str, str]) -> str:
    src = source_path(patch)
    if not src.is_file():
        raise RebaseError(f"missing {patch.origin} patch: {src}")

    body = src.read_text(encoding="utf-8", errors="surrogateescape").splitlines()
    message: list[str] = []
    if patch.origin == ISLAND:
        message, body = split_mailbox(body)

    dropped = sum(1 for line in body if DS_STORE_RE.match(line))
    body = [line for line in body if not DS_STORE_RE.match(line)]

    applied = [r for r in rules if r.patch == patch.filename]
    if applied and patch.origin == ISLAND:
        raise RebaseError(
            f"{patch.filename}: island members are never re-anchored. The lane is "
            "GENERATED upstream and byte-preserved here, so a hunk that stops "
            "applying at a new base is an island release, not a rule in "
            f"rebase/{pin['KERNEL_TAG']}.rules"
        )
    for rule in applied:
        body = apply_rule(body, rule)

    upstream_repo = pin["UPSTREAM_PATCHES_REPO"]
    upstream_rev = pin["UPSTREAM_PATCHES_REV"]
    tag = pin["KERNEL_TAG"]
    tested = pin["UPSTREAM_TESTED_KERNEL"]

    header: list[str] = [
        # mbox delimiter. For the upstream lane the hex is the upstream commit that
        # last touched this file, and for a merged backport it is the commit being
        # backported, so provenance is machine-readable rather than decorative; the
        # first-party lane has no such commit and uses NULL_OID, and an unmerged
        # lore posting uses the LORE_POSTING sentinel, which cannot be misread as
        # an object id of any kind.
        f"From {ISLAND_RELEASE if isinstance(patch.provenance, Island) else patch.provenance} "
        "Mon Sep 17 00:00:00 2001",
        f"From: {patch.author}",
        f"Date: {patch.date}",
        f"Subject: [PATCH {patch.ordinal}/{SERIES_TOTAL}] {patch.subject}",
        "",
    ]

    if patch.origin == UPSTREAM:
        header += [
            f"Imported from {upstream_repo}",
            f"at {upstream_rev}, file {patch.filename}.",
            "",
            "Authored by Ross Cawston. This CeraLive copy re-packages the file as a git",
            "mailbox so it can be applied with `git am`. Every added and removed line is",
            "byte-identical to upstream's; scripts/verify-payload-parity.py enforces that.",
            "",
        ]
    elif patch.origin == ISLAND:
        island = patch.provenance
        if not isinstance(island, Island):
            raise LaneError(
                f"{patch.filename}: the {ISLAND}/ lane must name its release"
            )
        asset = f"rk3588-media-island-{island.tag}.mbox.tar"
        member = island_member_name(patch)
        header += [
            *message,
            "",
            f"Generated from CeraLive rk3588-media-island {island.tag} "
            f"({island.commit}).",
            "",
            f"Release asset {asset}",
            f"  asset_sha256  {island.asset_sha256}",
            f"  member        {member}",
            f"  member_sha256 {hashlib.sha256(src.read_bytes()).hexdigest()}",
            "",
            f"{ISLAND}/{patch.filename} is that member byte-for-byte -- the mail",
            "header above is this repository's own, so the N/%d ordinal is ours and"
            % SERIES_TOTAL,
            "the message is the release's. scripts/verify-island-provenance.py",
            "re-fetches the asset, checks asset_sha256 and byte-compares every",
            "member, independently of scripts/build-series.py.",
            "",
        ]
    elif patch.origin == BACKPORTS and patch.lore is not None:
        lore = patch.lore
        header += [
            f"Backport of unmerged {lore.revision} posting.",
            "",
            lore.upstream_subject,
            "",
            *lore.note,
            *([""] if lore.note else []),
            f"Posted to lore on {lore.posted_date} as {lore.revision}:",
            f"https://lore.kernel.org/r/{lore.lore_msgid}",
            f"Review state: {lore.review_state}",
            "",
            "Canonical thread archive -- the only source an import may be taken",
            f"from: https://lore.kernel.org/all/{lore.lore_msgid}/t.mbox.gz",
            f"  thread_compressed_sha256 {lore.thread_compressed_sha256}",
            "    (the gzip response bytes, exactly as served)",
            f"  thread_mbox_sha256       {lore.thread_mbox_sha256}",
            "    (the mailbox those bytes decompress to)",
            f"  canonical_patch_sha256   {lore.canonical_patch_sha256}",
            f"    (this posting's canonical mail, archived at {lore.canonical_mail})",
            "",
            f"Backported into the CeraLive series for {tag}. The source of record is",
            f"{patch.origin}/{patch.filename}; patches/ is generated from it by",
            "scripts/build-series.py, and scripts/verify-payload-parity.py holds it to",
            "the same added/removed-line parity every other lane gets.",
            "",
        ]
    elif patch.origin == BACKPORTS:
        backport = patch.backport
        if backport is None:
            raise LaneError(
                f"{patch.filename}: the {BACKPORTS}/ lane must name its own origin"
            )
        header += [
            f"commit {patch.provenance} upstream.",
            "",
            backport.upstream_subject,
            "",
            *backport.note,
            *([""] if backport.note else []),
            f"Backported into the CeraLive series for {tag}. Posted at",
            f"https://lore.kernel.org/r/{backport.lore_msgid}",
            "",
            f"The source of record is {patch.origin}/{patch.filename}; patches/ is",
            "generated from it by scripts/build-series.py, and",
            "scripts/verify-payload-parity.py holds it to the same added/removed-line",
            "parity the imported and first-party lanes get.",
            "",
        ]
    else:
        header += [
            *patch.rationale,
            "",
            f"First-party: authored by CeraLive against {tag}, with no upstream",
            f"counterpart in {upstream_repo.rsplit('/', 1)[-1]}. The source of record is",
            f"{patch.origin}/{patch.filename}; patches/ is generated from it by",
            "scripts/build-series.py, and scripts/verify-payload-parity.py holds it to the",
            "same added/removed-line parity the upstream lane gets.",
            "",
        ]

    if dropped:
        header += [
            f'Dropped {dropped} payload-free "Binary files .../.DS_Store ... differ"',
            "stanza(s) that macOS left in the original `diff -ruN` output. They carry",
            "no data, and git apply refuses a binary stanza with no index line.",
            "",
        ]

    if applied:
        header += [
            f"Re-anchored for {tag} (upstream developed this against {tested}):",
        ]
        header += [
            f"  - {'replaced' if r.op == 'replace' else 'restored'} context line "
            f"`{r.anchor.strip()}`"
            for r in applied
        ]
        header += [
            "Context lines only -- see rebase/%s.rules and docs/REBASE-%s.md for the"
            % (tag, tag),
            "hunk-by-hunk ledger.",
            "",
        ]

    if patch.origin == UPSTREAM:
        header += [
            "NOT upstream-bound: this is a CeraLive-maintained adaptation, not a submission",
            f"to {upstream_repo.rsplit('/', 1)[-1]}. No Signed-off-by is added, because none",
            "was given upstream and inventing one would misattribute a DCO assertion.",
        ]
    elif patch.origin == ISLAND:
        header += [
            "NOT upstream-bound: the island is a CeraLive-maintained out-of-tree driver",
            "collection, not a submission. No commit id is claimed here. The island",
            "release names a tag and a commit in its OWN repository, which is not the",
            "kernel history this mailbox's delimiter field is for, so the delimiter",
            "carries a sentinel rather than a 40-hex value that would read as one.",
            "",
            "This lane is GENERATED UPSTREAM and byte-preserved here: never hand-edited,",
            "never re-anchored. A base bump is an island release first. Retire this when",
            "the island stops carrying the component -- trigger and last-checked date:",
            "docs/UPSTREAM-STATUS.md.",
        ]
    elif patch.origin == BACKPORTS and patch.lore is not None:
        header += [
            "NOT upstream: this posting has NOT been merged, so no commit id exists for",
            "it and none is claimed. This header deliberately carries no",
            "`commit <sha> upstream.` marker, no null object id and no parent SHA --",
            "there is no such identity to state, and stating one would be false",
            "provenance rather than a formatting shortcut. No Signed-off-by is added",
            "either: the DCO chain belongs to the author on the list.",
            "",
            "Retire this when the posting merges AND the pinned base absorbs it -- both,",
            "not either. Trigger and last-checked date: docs/UPSTREAM-STATUS.md.",
        ]
    elif patch.origin == BACKPORTS:
        header += [
            "ALREADY upstream: this is a backport, not a submission. No Signed-off-by is",
            "added here, because the DCO chain belongs to the original author and to",
            "whoever lands it on a stable tree -- the lore link above has the real one.",
        ]
    else:
        header += [
            "NOT upstream-bound: this targets the CeraLive device tree only and is not a",
            "submission to linux-media, linux-rockchip or the fork parent. No Signed-off-by",
            "is added, because a DCO assertion belongs to whoever actually submits it.",
        ]

    header += [
        "",
        "---",
    ]

    return "\n".join(header + body) + "\n"


def write_series(out_dir: Path, pin: dict[str, str]) -> None:
    retired = load_retired()
    check_membership(retired)

    rules = load_rules(pin["KERNEL_TAG"])

    known = {p.filename for p in SERIES}
    for rule in rules:
        if rule.patch not in known:
            raise RebaseError(
                f"rebase rule at line {rule.lineno} names unknown patch {rule.patch!r}"
            )

    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("*.patch"):
        stale.unlink()
    (out_dir / "series").unlink(missing_ok=True)

    for patch in SERIES:
        (out_dir / patch.filename).write_text(
            build_patch(patch, rules, pin), encoding="utf-8", errors="surrogateescape"
        )

    series_lines = [
        "# git-am order for the CeraLive RK3588 series.",
        "# Upstream numbering is preserved verbatim -- 0004 was never published,",
        "# so the gap is intentional. Do not renumber to close it.",
        # Derived, never hand-written: this line named three first-party ordinals
        # and would have silently gone stale the moment a fourth was added.
        "# First-party (ceralive/): " + ", ".join(
            f"{p.ordinal:04d}" for p in SERIES if p.origin == CERALIVE
        ) + ".",
        "# Backports (backports/): " + ", ".join(
            f"{p.ordinal:04d}" for p in SERIES if p.origin == BACKPORTS
        ) + " -- 0007 is a merged commit, the rest are unmerged lore postings.",
        "# All of them continue the same counter.",
        f"# Target kernel: {pin['KERNEL_TAG']} ({pin['KERNEL_COMMIT']})",
        *(
            f"# Retired slot {e.ordinal}: {e.filename} -- see retired/REGISTRY.md"
            for e in sorted(
                (entry for entry in retired.values() if entry.ordinal is not None),
                key=lambda entry: entry.ordinal,
            )
        ),
        *(p.filename for p in SERIES),
    ]
    (out_dir / "series").write_text("\n".join(series_lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify patches/ matches what this script would generate",
    )
    args = parser.parse_args()

    pin = read_pin()

    if not args.check:
        write_series(PATCHES_DIR, pin)
        print(f"wrote {len(SERIES)} patches + series to {PATCHES_DIR}")
        return 0

    with tempfile.TemporaryDirectory() as tmp:
        expected = Path(tmp) / "patches"
        write_series(expected, pin)

        names = sorted({p.name for p in expected.iterdir()})
        match, mismatch, errors = filecmp.cmpfiles(
            PATCHES_DIR, expected, names, shallow=False
        )
        if mismatch or errors:
            print("patches/ is STALE or hand-edited.", file=sys.stderr)
            for name in sorted(mismatch):
                print(f"  differs: {name}", file=sys.stderr)
            for name in sorted(errors):
                print(f"  missing: {name}", file=sys.stderr)
            print("Re-run scripts/build-series.py.", file=sys.stderr)
            return 1

        extra = sorted({p.name for p in PATCHES_DIR.iterdir()} - set(names))
        if extra:
            print(f"unexpected files in patches/: {extra}", file=sys.stderr)
            return 1

        print(f"patches/ is in sync ({len(match)} files).")
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SeriesError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
