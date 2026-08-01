#!/usr/bin/env bash
#
# preflight.sh — re-resolve the Armbian rk3588 `edge` kernel mapping from source
# and report drift against kernel-pin.env.
#
# The mapping is spread over four Armbian files and is NOT obvious: the rk3588
# family config handles only `legacy` and `vendor`, so `edge` is decided by the
# common include it sources, and the kernel branch is decided later still by a
# hook. Anyone bumping this repo's pin should run this rather than trust a number
# copied from a previous investigation.
#
# Read-only. Never edits kernel-pin.env; it prints what it found and exits
# non-zero on a mismatch so CI can fail on it.
#
# Usage:
#   scripts/preflight.sh              # check against the pinned ARMBIAN_BUILD_REV
#   scripts/preflight.sh --head       # check against armbian/build's CURRENT main
#
# `--head` is the one that matters when deciding to bump: it answers "has Armbian
# moved edge since we pinned?".

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${HERE}/.." && pwd)"

# shellcheck source=../kernel-pin.env
source "${ROOT}/kernel-pin.env"

RAW="https://raw.githubusercontent.com/armbian/build"
API="https://api.github.com/repos/armbian/build"

rev="${ARMBIAN_BUILD_REV}"
mode="pinned"
if [[ "${1:-}" == "--head" ]]; then
	mode="current HEAD"
	# Unauthenticated api.github.com is 60 req/h per IP, which shared CI runners
	# do exhaust. Use the workflow token when there is one so this cannot flake.
	declare -a auth=()
	[[ -n "${GITHUB_TOKEN:-}" ]] && auth=(-H "Authorization: Bearer ${GITHUB_TOKEN}")
	rev="$(curl -fsSL "${auth[@]}" "${API}/commits/main" |
		sed -n 's/.*"sha": *"\([0-9a-f]\{40\}\)".*/\1/p' | head -1)"
	[[ -n "${rev}" ]] || { echo "error: could not resolve armbian/build main" >&2; exit 2; }
fi

echo "armbian/build @ ${rev} (${mode})"
echo

tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT

fetch() {
	curl -fsSL "${RAW}/${rev}/$1" -o "${tmp}/$(basename "$1")" ||
		{ echo "error: cannot fetch $1 at ${rev}" >&2; exit 2; }
}

fetch config/sources/families/rockchip-rk3588.conf
fetch config/sources/families/include/rockchip64_common.inc
fetch config/sources/mainline-kernel.conf.sh
for board in ${ARMBIAN_BOARDS}; do fetch "config/boards/${board}.conf"; done

status=0
check() {
	local label="$1" want="$2" got="$3"
	if [[ "${want}" == "${got}" ]]; then
		printf '  ok    %-26s %s\n' "${label}" "${got}"
	else
		printf '  DRIFT %-26s pinned=%s  actual=%s\n' "${label}" "${want}" "${got}" >&2
		status=1
	fi
}

# --- boards -----------------------------------------------------------------
echo "Board -> family"
for board in ${ARMBIAN_BOARDS}; do
	family="$(sed -n 's/^BOARDFAMILY="\(.*\)"$/\1/p' "${tmp}/${board}.conf" | head -1)"
	targets="$(sed -n 's/^KERNEL_TARGET="\(.*\)"$/\1/p' "${tmp}/${board}.conf" | head -1)"
	check "${board} family" "${ARMBIAN_BOARDFAMILY}" "${family}"
	if [[ ",${targets}," == *",${ARMBIAN_BRANCH},"* ]]; then
		printf '  ok    %-26s KERNEL_TARGET=%s\n' "${board} supports edge" "${targets}"
	else
		printf '  DRIFT %-26s KERNEL_TARGET=%s lacks %s\n' \
			"${board}" "${targets}" "${ARMBIAN_BRANCH}" >&2
		status=1
	fi
done

# --- does the family config still delegate `edge` to the common include? -----
echo
echo "Family config delegation"
if grep -qE '^\s*edge\)' "${tmp}/rockchip-rk3588.conf"; then
	echo "  DRIFT rockchip-rk3588.conf now handles 'edge' itself." >&2
	echo "        kernel-pin.env's derivation assumes it does NOT. Re-read it." >&2
	status=1
else
	echo "  ok    rockchip-rk3588.conf has no edge) case; rockchip64_common.inc decides"
fi

# --- the actual mapping ------------------------------------------------------
echo
echo "BRANCH=${ARMBIAN_BRANCH} mapping (rockchip64_common.inc)"
edge_block="$(awk '/^[[:space:]]*edge\)/{f=1} f{print} f&&/;;/{exit}' \
	"${tmp}/rockchip64_common.inc")"
mm="$(sed -n 's/.*KERNEL_MAJOR_MINOR="\([^"]*\)".*/\1/p' <<<"${edge_block}" | head -1)"
lf="$(sed -n 's/.*LINUXFAMILY=\([A-Za-z0-9_]*\).*/\1/p'  <<<"${edge_block}" | head -1)"
check "KERNEL_MAJOR_MINOR" "${KERNEL_MAJOR_MINOR}" "${mm}"
check "LINUXFAMILY"        "${LINUXFAMILY}"        "${lf}"

# --- kernel branch default ---------------------------------------------------
echo
echo "Kernel branch default (mainline-kernel.conf.sh)"
if grep -q 'KERNELBRANCH="branch:linux-${KERNEL_MAJOR_MINOR}.y"' \
	"${tmp}/mainline-kernel.conf.sh"; then
	check "KERNELBRANCH" "${KERNELBRANCH_ARMBIAN}" "branch:linux-${mm}.y"
else
	echo "  DRIFT the __900_defaults hook no longer derives branch:linux-<mm>.y" >&2
	status=1
fi

if grep -qE "KERNEL_MAJOR_MINOR}\" == \"${mm}\"" "${tmp}/mainline-kernel.conf.sh"; then
	echo "  NOTE  ${mm} now has an explicit override hook; the rolling-branch default"
	echo "        no longer applies. Re-read mainline-kernel.conf.sh before bumping."
	status=1
fi

echo
if (( status == 0 )); then
	echo "PREFLIGHT OK — kernel-pin.env matches armbian/build @ ${rev}"
else
	echo "PREFLIGHT DRIFT — kernel-pin.env is stale for armbian/build @ ${rev}" >&2
	echo "Update kernel-pin.env and docs/PREFLIGHT.md together, then re-run." >&2
fi
exit "${status}"
