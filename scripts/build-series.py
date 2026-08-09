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

Three lanes, one pipeline
-------------------------
``upstream/`` holds Ross Cawston's files verbatim. ``ceralive/`` holds first-party
patches this project authored, which have no upstream counterpart. ``backports/``
holds patches taken from somewhere else entirely -- mainline, a stable tree, or a
posting on lore -- which is why every member of that lane must name its own origin
(the mainline commit it is a backport of, and the lore Message-ID it was posted
under) instead of inheriting one blanket credit line the way ``upstream/`` does.
All three lanes go through the same converter so that ``patches/`` stays fully
generated -- the whole point of the ANTI-PATTERN "don't hand-edit patches/". The
lane only changes the mail header the converter writes and which directory parity
is proven against; every other guarantee is shared.

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
SOURCE_DIRS = {
    UPSTREAM: ROOT / UPSTREAM,
    CERALIVE: ROOT / CERALIVE,
    BACKPORTS: ROOT / BACKPORTS,
}

# Only *.patch is a series candidate. Both upstream/README.MD and the per-lane
# READMEs live beside the patches and are not part of any lane's membership.
LANE_GLOB = "*.patch"

REGISTRY_COLUMNS = ("Patch", "Lane", "Ordinal", "Retired", "Kernel tag", "Reason")
REGISTRY_RULE_RE = re.compile(r"^:?-{3,}:?$")
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")

# Slot count, not member count. 0004 was never published upstream and we keep the
# gap so our files line up 1:1 with theirs, hence ordinals 1/9, 2/9, 3/9, 5/9, 6/9.
# 0007 continues the same counter into the backports/ lane, and 0008 and 0009 back
# into ceralive/.
SERIES_TOTAL = 9

DS_STORE_RE = re.compile(r"^Binary files .*\.DS_Store .* differ$")
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")


# A first-party patch has no originating commit anywhere, so the mbox delimiter
# carries the null object id rather than a borrowed or invented one.
NULL_OID = "0" * 40


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
class Patch:
    """One member of the series."""

    filename: str
    ordinal: int
    subject: str
    provenance: str  # commit of origin: upstream's, the backported one, or NULL_OID
    author: str
    date: str
    origin: str = UPSTREAM
    rationale: tuple[str, ...] = ()  # first-party lane only: why this patch exists
    backport: Backport | None = None  # backports lane only, and mandatory there


SERIES: tuple[Patch, ...] = (
    Patch(
        filename="0001-rockchip-rk3588-vepu580-encoder-support-v3.patch",
        ordinal=1,
        subject=(
            "rockchip: rk3588: add VEPU580 (RKVENC v2) "
            "H.265/H.264/JPEG encoder support"
        ),
        provenance="09595583f3ffadd3d790a20ead392434e0e46728",
        author="Ross Cawston <rcawston@users.noreply.github.com>",
        date="Mon, 9 Feb 2026 20:42:16 -0800",
    ),
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
        author="CeraLive <dev@ceralive.tv>",
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
        filename="0007-iommu-rockchip-disable-fetch-dte-time-limit.patch",
        ordinal=7,
        subject="iommu/rockchip: disable fetch dte time limit",
        provenance="8d4346ecd4950ae08cc76a6de327c264e846758c",
        author="Simon Xue <xxm@rock-chips.com>",
        date="Tue, 28 Apr 2026 18:05:31 +0200",
        origin=BACKPORTS,
        backport=Backport(
            upstream_subject="iommu/rockchip: disable fetch dte time limit",
            lore_msgid="20260428-spu-iommudtefix-v2-1-f592f579e508@pengutronix.de",
            note=(
                "RK3588's IOMMU blocks after four consecutive DTE fetches race a CPU-side",
                "page-table update, which the vendor kernel works around by setting BIT(31)",
                "of MMU_AUTO_GATING. Upstream carried the bug until 7.2-rc1; the symptom on",
                "RK356x/RK3588 is a blocked VOP and a black screen, and on RK3588 also",
                "sporadic RGA3 hangs. Nothing in v7.1.7 sets that bit -- the base has",
                "RK_MMU_AUTO_GATING but never writes DISABLE_FETCH_DTE_TIME_LIMIT -- so the",
                "pinned kernel takes the hang, and this series drives exactly the VOP and",
                "media paths that trip it.",
                "",
                "Applied to v7.1.7 with no context adaptation: the payload is byte-identical",
                "to 8d4346ecd495 and forward-applies with no fuzz. No prerequisite commits;",
                "RK_MMU_AUTO_GATING and rk_iommu_read/write already exist in the base.",
                "",
                "Merged for 7.2-rc1 (Acked-by Heiko Stuebner, applied by Joerg Roedel). It",
                "carries no Fixes: tag and no Cc: stable, so 7.1.y will not pick it up on its",
                "own. Retire this backport when the pinned base reaches v7.2.",
            ),
        ),
    ),
    Patch(
        filename="0008-rkvenc-set-dma-max-segment-size.patch",
        ordinal=8,
        subject=(
            "media: rockchip: rkvenc: set the DMA max segment size "
            "in the hardware probe"
        ),
        provenance=NULL_OID,
        author="CeraLive <dev@ceralive.tv>",
        date="Sat, 8 Aug 2026 12:00:00 -0500",
        origin=CERALIVE,
        rationale=(
            "*** UNVALIDATED ON HARDWARE. *** This compiles and is source-correct; the",
            "runtime behaviour it predicts has NOT been observed on a board. Do not read",
            "it as a claim that MPP hardware encode now works on the edge track.",
            "",
            "Origin: the root-cause analysis recorded as defect 2 of 3 in the CeraLive",
            "image-building-pipeline AGENTS.md KNOWN ISSUE on MPP hardware video encode",
            "not working on the edge kernel -- a Rock 5B+ board diagnosis, 2026-08-02.",
            "",
            "rkvenc_dma_import_fd() records an imported dma-buf's length as",
            "sg_dma_len(sgt->sgl) -- the FIRST mapped segment only, not the mapping's total",
            "length. That is only ever correct when the mapping is a single segment, and",
            "0001 never told the DMA layer how long a segment may be. dma_get_max_seg_size()",
            "therefore answers its SZ_64K default (include/linux/dma-mapping.h), and",
            "iommu-dma's __finalise_sg() stops coalescing at that boundary",
            "(drivers/iommu/dma-iommu.c: max_len = dma_get_max_seg_size(dev), then",
            "`max_len - cur_len >= s_length`). Every import larger than 64 KiB is recorded",
            "as exactly 0x10000 bytes -- which is the window width the board reported, in",
            "every failing case.",
            "",
            "Expected effect: with the cap raised to the device's 32-bit addressing width,",
            "an imported buffer's recorded length becomes the FULL buffer length, so a",
            "frame's plane offsets resolve inside the mapped window instead of past its",
            "truncated end.",
            "",
            "The IOVA guardrail in rkvenc_service.c is deliberately NOT touched. It is",
            "correct: it rejects a register that genuinely points outside the window this",
            "bookkeeping described, and with that window truncated to 64 KiB an NV12",
            "chroma-plane offset genuinely is outside it. Silencing the guardrail would hide",
            "the defect one layer down instead of fixing it, and would trade a clean -EINVAL",
            "for a DMA write past the end of a mapping.",
            "",
            "The call is checked, not fire-and-forget -- but NOT by its return value, which",
            "does not exist at this base. At v7.1.7 dma_set_max_seg_size() returns void and",
            "merely WARN_ON_ONCE()s when dev->dma_parms is NULL, leaving the SZ_64K default",
            "in place. So the probe reads the value back with dma_get_max_seg_size() and",
            "fails with -EINVAL if it did not take: that verifies the EFFECT rather than a",
            "status, and the state it refuses to boot into is exactly the defect above. The",
            "platform bus does point dma_parms at the platform_device's own storage",
            "(drivers/base/platform.c setup_pdev_dma_masks), so this is expected to pass on",
            "every rkvenc core; the check exists so a future base that changes that fails",
            "loudly at probe rather than silently truncating every frame.",
            "",
            "Placed before pm_runtime_enable()/device_init_wakeup(), so the failure path is",
            "a plain return rather than the `failed` label -- unwinding there would call",
            "pm_runtime_disable() without a matching enable.",
            "",
            "This is one of THREE stacked defects on that track. It does not address the",
            "other two, both of which are userspace/heap problems: librockchip-mpp asks for",
            "a `system-uncached` dma-heap that mainline does not register, and mainline has",
            "no uncached heap for it to fall back to.",
        ),
    ),
    Patch(
        filename="0009-dma-buf-heaps-add-system-uncached-dma-heap.patch",
        ordinal=9,
        subject="dma-buf: heaps: add a system-uncached heap",
        provenance=NULL_OID,
        author="CeraLive <dev@ceralive.tv>",
        date="Sun, 9 Aug 2026 12:00:00 -0500",
        origin=CERALIVE,
        rationale=(
            "*** UNVALIDATED ON HARDWARE. *** This compiles and is source-correct against",
            "the pinned base; nothing it predicts has been observed on a board. Do not read",
            "it as a claim that MPP hardware encode now works on the edge track.",
            "",
            "*** HARDWARE PROOF IS MANDATORY FOR THIS PATCH, NOT OPTIONAL. *** Everything",
            "else in this series can be argued from source. This one cannot, and the reason",
            "is stated plainly below under CACHE ALIASING: a compile proves the heap exists,",
            "and a heap that exists while getting cache maintenance subtly wrong produces",
            "intermittent, silent corruption in the video path rather than an error. The",
            "checklist that must pass before anyone calls this working is",
            "docs/BOARD-QUALIFICATION.md.",
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
    ordinal: int
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
        if lane not in SOURCE_DIRS:
            raise LaneError(
                f"{REGISTRY_FILE.name}:{lineno}: lane {lane!r} is not one of "
                f"{sorted(SOURCE_DIRS)}"
            )
        if not ordinal.isdigit():
            raise LaneError(
                f"{REGISTRY_FILE.name}:{lineno}: ordinal {ordinal!r} is not a number"
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
            ordinal=int(ordinal),
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
            if patch.backport is None:
                problems.append(
                    f"{where}: the {BACKPORTS}/ lane must name its own origin; "
                    "give it a Backport(upstream_subject=..., lore_msgid=...)"
                )
            # NULL_OID is 40 hex digits, so the shape test alone would let a
            # provenance-less backport through -- and "no originating commit" is
            # the one thing a backport cannot be.
            if patch.provenance == NULL_OID or not SHA1_RE.match(patch.provenance):
                problems.append(
                    f"{where}: a backport's provenance must be the 40-hex commit "
                    f"it is backported from, not {patch.provenance!r}"
                )
        elif patch.backport is not None:
            problems.append(f"{where}: only the {BACKPORTS}/ lane carries a Backport")
        if patch.origin == CERALIVE and not patch.rationale:
            problems.append(f"{where}: a first-party patch must state why it exists")
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

    archived = (
        {p.name for p in RETIRED_DIR.glob(LANE_GLOB)} if RETIRED_DIR.is_dir() else set()
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


def build_patch(patch: Patch, rules: list[Rule], pin: dict[str, str]) -> str:
    src = source_path(patch)
    if not src.is_file():
        raise RebaseError(f"missing {patch.origin} patch: {src}")

    body = src.read_text(encoding="utf-8", errors="surrogateescape").splitlines()

    dropped = sum(1 for line in body if DS_STORE_RE.match(line))
    body = [line for line in body if not DS_STORE_RE.match(line)]

    applied = [r for r in rules if r.patch == patch.filename]
    for rule in applied:
        body = apply_rule(body, rule)

    upstream_repo = pin["UPSTREAM_PATCHES_REPO"]
    upstream_rev = pin["UPSTREAM_PATCHES_REV"]
    tag = pin["KERNEL_TAG"]
    tested = pin["UPSTREAM_TESTED_KERNEL"]

    header: list[str] = [
        # mbox delimiter. For the upstream lane the hex is the upstream commit that
        # last touched this file, and for a backport it is the commit being
        # backported, so provenance is machine-readable rather than decorative; the
        # first-party lane has no such commit and uses NULL_OID.
        f"From {patch.provenance} Mon Sep 17 00:00:00 2001",
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
        "# 0006 and 0008 are first-party (ceralive/) and 0007 is a backport",
        "# (backports/); all three continue the same counter.",
        f"# Target kernel: {pin['KERNEL_TAG']} ({pin['KERNEL_COMMIT']})",
        *(
            f"# Retired slot {e.ordinal}: {e.filename} -- see retired/REGISTRY.md"
            for e in sorted(retired.values(), key=lambda e: e.ordinal)
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
