#!/usr/bin/env bash
#
# apply.sh — apply the series to a kernel tree at the pinned tag.
#
# This is both the operator entry point and the CI gate, deliberately: a README
# instruction that CI does not execute is an instruction that rots. Everything the
# README tells a human to run, this script runs.
#
# Usage:
#   scripts/apply.sh                       # clone into ./.work/linux, then apply
#   scripts/apply.sh /path/to/linux        # apply to an existing tree
#   KEEP_TREE=1 scripts/apply.sh           # keep ./.work/linux for inspection
#   scripts/apply.sh --keep <dir>          # keep the verified tree AT <dir>
#
# It refuses to touch a tree with local modifications, and resets to the pinned
# tag before applying, so a rerun is always a clean run.
#
# --keep <dir> exists for tests/build-rkvenc-harness.sh. That harness has to
# compile against the UAPI of the EXACT applied series, and this repository
# holds no kernel source of its own -- so rather than let a harness build its
# own tree (which could be anything), it is handed one this script has already
# verified: pinned base commit, full series applied, post-apply checks passed.
# The directory is a normal path, not a hidden scratch dir, precisely so the
# caller can point at it and assert what it is.

set -euo pipefail

KEEP_DIR=""
ARGS=()
while (( $# )); do
	case "$1" in
		--keep)   KEEP_DIR="${2:-}"; shift 2 ;;
		--keep=*) KEEP_DIR="${1#--keep=}"; shift ;;
		*)        ARGS+=("$1"); shift ;;
	esac
done
if [[ -n "${KEEP_DIR}" ]]; then
	[[ "${KEEP_DIR}" == /* ]] \
		|| { echo "error: --keep needs an absolute path (got '${KEEP_DIR}')" >&2; exit 2; }
	set -- "${KEEP_DIR}" "${ARGS[@]+"${ARGS[@]}"}"
else
	set -- "${ARGS[@]+"${ARGS[@]}"}"
fi

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${HERE}/.." && pwd)"

# shellcheck source=../kernel-pin.env
source "${ROOT}/kernel-pin.env"

WORKDIR="${ROOT}/.work"
TREE="${1:-${WORKDIR}/linux}"
CLONE_SOURCE="${KERNEL_CLONE_SOURCE:-${KERNEL_MIRROR}}"

log() { printf '\n== %s\n' "$*"; }

# ---------------------------------------------------------------------------
# 1. Series integrity — patches/ must be exactly what the converter produces
#    from its source lanes, and it must not have changed what those patches do.
# ---------------------------------------------------------------------------
log "Verifying patches/ is generated, not hand-edited"
python3 "${HERE}/build-series.py" --check

log "Verifying the series changes nothing its source lanes did not already change"
python3 "${HERE}/verify-payload-parity.py"

log "Verifying island/ against the published rk3588-media-island release"
python3 "${HERE}/verify-island-provenance.py"

# ---------------------------------------------------------------------------
# 2. Kernel tree at the pinned tag.
# ---------------------------------------------------------------------------
if [[ ! -d "${TREE}/.git" ]]; then
	log "Cloning ${CLONE_SOURCE} at ${KERNEL_TAG} into ${TREE}"
	mkdir -p "$(dirname "${TREE}")"
	git clone --depth 1 --branch "${KERNEL_TAG}" --single-branch \
		"${CLONE_SOURCE}" "${TREE}"
else
	log "Using existing kernel tree ${TREE}"
fi

cd "${TREE}"

if [[ -n "$(git status --porcelain)" ]]; then
	echo "error: ${TREE} has local changes; refusing to reset it." >&2
	echo "       Commit, stash, or point apply.sh at a scratch tree." >&2
	exit 1
fi

# Assert BOTH pinned coordinates, and read them from refs/tags/ explicitly so a
# same-named branch cannot shadow the tag. The peeled commit alone cannot see a tag
# object that was re-created — re-signed, re-dated, re-worded — while still pointing
# at the same commit, and the tag object is what a signature is verified against.
if ! git rev-parse --verify --quiet "refs/tags/${KERNEL_TAG}" >/dev/null; then
	echo "error: ${TREE} has no refs/tags/${KERNEL_TAG}." >&2
	echo "       Clone with --branch ${KERNEL_TAG}, or fetch the tag. Not applying." >&2
	exit 1
fi

actual_tag_object="$(git rev-parse "refs/tags/${KERNEL_TAG}")"
actual_commit="$(git rev-parse "refs/tags/${KERNEL_TAG}^{commit}")"
pin_ok=1

if [[ "$(git cat-file -t "refs/tags/${KERNEL_TAG}")" != "tag" ]]; then
	echo "error: refs/tags/${KERNEL_TAG} is not an annotated tag object." >&2
	echo "       linux-stable tags are annotated, so this tree was either fetched" >&2
	echo "       without them or the tag is not upstream's." >&2
	pin_ok=0
elif [[ "${actual_tag_object}" != "${KERNEL_TAG_OBJECT}" ]]; then
	echo "error: refs/tags/${KERNEL_TAG} is tag object ${actual_tag_object}," >&2
	echo "       but kernel-pin.env pins ${KERNEL_TAG_OBJECT}." >&2
	pin_ok=0
fi

if [[ "${actual_commit}" != "${KERNEL_COMMIT}" ]]; then
	echo "error: ${KERNEL_TAG} resolves to commit ${actual_commit}," >&2
	echo "       but kernel-pin.env pins ${KERNEL_COMMIT}." >&2
	pin_ok=0
fi

if (( pin_ok == 0 )); then
	echo "       A tag moved, or the tree is not linux-stable. Not applying." >&2
	exit 1
fi
log "Kernel tree at ${KERNEL_TAG} (tag ${actual_tag_object}, commit ${actual_commit})"

# `git am` needs an identity even when nothing is committed by a human.
git config user.name  >/dev/null 2>&1 || git config user.name  "CeraLive Patch Gate"
git config user.email >/dev/null 2>&1 || git config user.email "noreply@ceralive.tv"

git am --abort >/dev/null 2>&1 || true
git checkout -f "${KERNEL_TAG}" --quiet
git clean -fdxq

# ---------------------------------------------------------------------------
# 3. Apply. Order is patches/series, which is upstream's lexical order.
# ---------------------------------------------------------------------------
mapfile -t SERIES < <(grep -v '^\s*#' "${ROOT}/patches/series" | grep -v '^\s*$')
log "Applying ${#SERIES[@]} patches with git am"

declare -a ABS=()
for name in "${SERIES[@]}"; do
	ABS+=("${ROOT}/patches/${name}")
done

if ! git am --keep-non-patch "${ABS[@]}"; then
	echo >&2
	echo "error: the series does not apply to ${KERNEL_TAG}." >&2
	echo "       Failing patch: $(git am --show-current-patch=raw 2>/dev/null |
		sed -n 's/^Subject: //p' | head -1)" >&2
	echo "       Inspect with: git -C ${TREE} am --show-current-patch=diff" >&2
	echo "       Do NOT invent a resolution. Ledger the conflict in" >&2
	echo "       docs/REBASE-${KERNEL_TAG}.md and add a context-only rule to" >&2
	echo "       rebase/${KERNEL_TAG}.rules only if it is provably behaviour-neutral." >&2
	git am --abort >/dev/null 2>&1 || true
	exit 1
fi

log "Applied cleanly"
git log --oneline "${KERNEL_TAG}..HEAD"
echo
git diff --stat "${KERNEL_TAG}..HEAD"

# ---------------------------------------------------------------------------
# 4. Post-conditions worth asserting: the island modules, clients and in-tree DT
#    ownership landed, and the HDMI-RX audio card remains wired on both boards.
# ---------------------------------------------------------------------------
log "Post-apply checks"
fail=0
for path in \
	drivers/video/rockchip/mpp/mpp_service.c \
	drivers/video/rockchip/mpp/mpp_rkvenc2.c \
	drivers/video/rockchip/mpp/mpp_rkvdec2.c \
	drivers/video/rockchip/mpp/mpp_jpgdec.c \
	drivers/video/rockchip/rga3/rga_drv.c \
	include/uapi/linux/rk-mpp.h; do
	if [[ -f "${path}" ]]; then
		echo "  ok      ${path}"
	else
		echo "  MISSING ${path}" >&2
		fail=1
	fi
done

if grep -q 'obj-$(CONFIG_ROCKCHIP_MPP_SERVICE) += rk_vcodec.o' \
	drivers/video/rockchip/mpp/Makefile; then
	echo "  ok      CONFIG_ROCKCHIP_MPP_SERVICE builds rk_vcodec.ko"
else
	echo "  MISSING rk_vcodec.ko module mapping" >&2
	fail=1
fi

if grep -q 'obj-$(CONFIG_ROCKCHIP_MULTI_RGA).*+= rga_multicore.o' \
	drivers/video/rockchip/rga3/Makefile; then
	echo "  ok      CONFIG_ROCKCHIP_MULTI_RGA builds rga_multicore.ko"
else
	echo "  MISSING rga_multicore.ko module mapping" >&2
	fail=1
fi

for symbol in \
	ROCKCHIP_MPP_SERVICE \
	ROCKCHIP_MPP_RKVENC2 \
	ROCKCHIP_MPP_RKVDEC2 \
	ROCKCHIP_MPP_JPGDEC; do
	if grep -q "^config ${symbol}$" drivers/video/rockchip/mpp/Kconfig; then
		echo "  ok      CONFIG_${symbol} is selectable"
	else
		echo "  MISSING CONFIG_${symbol} in mpp/Kconfig" >&2
		fail=1
	fi
done

if grep -q '^menuconfig ROCKCHIP_MULTI_RGA$' drivers/video/rockchip/rga3/Kconfig; then
	echo "  ok      CONFIG_ROCKCHIP_MULTI_RGA is selectable"
else
	echo "  MISSING CONFIG_ROCKCHIP_MULTI_RGA in rga3/Kconfig" >&2
	fail=1
fi

for label in mpp_srv rkvenc_ccu rkvdec_ccu jpegd; do
	if grep -q "^\s*${label}: " arch/arm64/boot/dts/rockchip/rk3588-base.dtsi; then
		echo "  ok      shared RK3588 dts node ${label}"
	else
		echo "  MISSING dts node ${label}" >&2
		fail=1
	fi
done

vdec0_block="$(awk '/^\tvdec0: /,/^\t};/' arch/arm64/boot/dts/rockchip/rk3588-base.dtsi)"
if [[ "$(grep -c '^\s*compatible = ' <<<"${vdec0_block}")" == 1 ]] && \
	grep -q '^\s*compatible = "rockchip,rkv-decoder-v2";$' <<<"${vdec0_block}"; then
	echo "  ok      vdec0 has the sole compatible rockchip,rkv-decoder-v2"
else
	echo "  MISSING sole rockchip,rkv-decoder-v2 compatible on vdec0" >&2
	fail=1
fi

for rga in \
	'fdb60000:rga3_core0:rockchip,rga3_core0' \
	'fdb70000:rga3_core1:rockchip,rga3_core1' \
	'fdb80000:rga:rockchip,rga2_core0'; do
	IFS=: read -r address label compatible <<<"${rga}"
	rga_block="$(awk "/^\\t${label}: /,/^\\t};/" arch/arm64/boot/dts/rockchip/rk3588-base.dtsi)"
	if [[ "$(grep -c '^\s*compatible = ' <<<"${rga_block}")" == 1 ]] && \
		grep -q "^\\s*compatible = \"${compatible}\";$" <<<"${rga_block}"; then
		echo "  ok      ${address} has the sole compatible ${compatible}"
	else
		echo "  MISSING sole ${compatible} compatible on ${address}" >&2
		fail=1
	fi
done

# 0009's entire userspace contract is the heap NAME: librockchip-mpp opens
# /dev/dma_heap/system-uncached by hard-coded string and has no override. A typo
# is therefore silent — a node appears, under a name nothing asks for — so assert
# the literal rather than the feature.
if grep -q '"system-uncached"' drivers/dma-buf/heaps/system_heap.c; then
	echo "  ok      the system-uncached heap name is spelled exactly"
else
	echo "  MISSING the literal \"system-uncached\" in system_heap.c" >&2
	fail=1
fi

if grep -q 'DMABUF_HEAPS_SYSTEM_UNCACHED' drivers/dma-buf/heaps/Kconfig; then
	echo "  ok      CONFIG_DMABUF_HEAPS_SYSTEM_UNCACHED is selectable"
else
	echo "  MISSING DMABUF_HEAPS_SYSTEM_UNCACHED in dma-buf/heaps/Kconfig" >&2
	fail=1
fi

# 0043 registers the codec; 0044/0045/0049 bind it on both boards. Assert
# both halves, and assert them per board: enabling hdmi_receiver without also
# enabling hdmirx_sound + i2s7_8ch is precisely the silent no-capture-card state
# that shipped before, and it is invisible until someone runs arecord on hardware.
DTS_DIR="arch/arm64/boot/dts/rockchip"

if grep -q "HDMI_CODEC_DRV_NAME" \
	drivers/media/platform/synopsys/hdmirx/snps_hdmirx.c; then
	echo "  ok      hdmirx registers an ASoC codec device"
else
	echo "  MISSING hdmi-audio-codec registration in snps_hdmirx.c" >&2
	fail=1
fi

for label in hdmi_receiver_sound hdmiin_codec; do
	if grep -q "${label}" "${DTS_DIR}/rk3588-extra.dtsi"; then
		echo "  ok      dts node ${label}"
	else
		echo "  MISSING dts node ${label} in rk3588-extra.dtsi" >&2
		fail=1
	fi
done

if awk '/^\thdmi_receiver: /,/^\t};/' "${DTS_DIR}/rk3588-extra.dtsi" |
	grep -q '#sound-dai-cells = <1>;'; then
	echo "  ok      hdmi_receiver is a sound-dai provider"
else
	echo "  MISSING #sound-dai-cells on hdmi_receiver" >&2
	fail=1
fi

# The two CeraLive boards (ARMBIAN_BOARDS in kernel-pin.env) must enable both
# halves. Other mainline boards are none of this series' business.
for board in rk3588-rock-5b.dtsi rk3588-orangepi-5-plus.dts; do
	for ref in hdmi_receiver_sound i2s7_8ch; do
		if grep -qE "^&${ref} \{" "${DTS_DIR}/${board}"; then
			echo "  ok      ${board} enables &${ref}"
		else
			echo "  MISSING &${ref} in ${board}" >&2
			fail=1
		fi
	done
done

python3 "${ROOT}/tests/test_hdmirx_audio_v4.py" --tree "${TREE}"

(( fail == 0 )) || exit 1

if [[ -n "${KEEP_DIR}" ]]; then
	log "Keeping the verified tree at ${KEEP_DIR}"
elif [[ -z "${KEEP_TREE:-}" && "${TREE}" == "${WORKDIR}/linux" ]]; then
	log "Removing ${WORKDIR} (set KEEP_TREE=1 to keep it)"
	cd "${ROOT}"
	rm -rf "${WORKDIR}"
fi

log "OK — series applies to ${KERNEL_TAG}"
