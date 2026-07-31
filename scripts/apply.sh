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
#
# It refuses to touch a tree with local modifications, and resets to the pinned
# tag before applying, so a rerun is always a clean run.

set -euo pipefail

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
#    from upstream/, and it must not have changed what upstream's patches do.
# ---------------------------------------------------------------------------
log "Verifying patches/ is generated, not hand-edited"
python3 "${HERE}/build-series.py" --check

log "Verifying the series changes nothing upstream/ did not already change"
python3 "${HERE}/verify-payload-parity.py"

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

actual_commit="$(git rev-parse "${KERNEL_TAG}^{commit}")"
if [[ "${actual_commit}" != "${KERNEL_COMMIT}" ]]; then
	echo "error: ${KERNEL_TAG} resolves to ${actual_commit}," >&2
	echo "       but kernel-pin.env pins ${KERNEL_COMMIT}." >&2
	echo "       A tag moved, or the tree is not linux-stable. Not applying." >&2
	exit 1
fi
log "Kernel tree at ${KERNEL_TAG} (${actual_commit})"

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
# 4. Post-conditions worth asserting: the encoder driver and its UAPI header
#    actually landed, and the DT overlay's node labels exist to bind against.
# ---------------------------------------------------------------------------
log "Post-apply checks"
fail=0
for path in \
	drivers/media/platform/rockchip/rkvenc/rkvenc_drv.c \
	drivers/media/platform/rockchip/rkvenc/rkvenc_service.c \
	include/uapi/linux/rkvenc.h; do
	if [[ -f "${path}" ]]; then
		echo "  ok      ${path}"
	else
		echo "  MISSING ${path}" >&2
		fail=1
	fi
done

for label in mpp_srv rkvenc_ccu rkvenc0 rkvenc1; do
	if grep -q "^\s*${label}: " arch/arm64/boot/dts/rockchip/rk3588-base.dtsi; then
		echo "  ok      dts node ${label}"
	else
		echo "  MISSING dts node ${label}" >&2
		fail=1
	fi
done

if grep -q "${RKVENC_CONFIG_SYMBOL#CONFIG_}" \
	drivers/media/platform/rockchip/rkvenc/Kconfig; then
	echo "  ok      ${RKVENC_CONFIG_SYMBOL} is selectable"
else
	echo "  MISSING ${RKVENC_CONFIG_SYMBOL} in rkvenc/Kconfig" >&2
	fail=1
fi

(( fail == 0 )) || exit 1

if [[ -z "${KEEP_TREE:-}" && "${TREE}" == "${WORKDIR}/linux" ]]; then
	log "Removing ${WORKDIR} (set KEEP_TREE=1 to keep it)"
	cd "${ROOT}"
	rm -rf "${WORKDIR}"
fi

log "OK — series applies to ${KERNEL_TAG}"
