#!/usr/bin/env bash
#
# preflight.sh — re-resolve the Armbian rk3588 kernel mapping for the branch
# named in kernel-pin.env (ARMBIAN_BRANCH) and report drift against that file.
#
# The mapping is spread over four Armbian files and is NOT obvious: the rk3588
# family config handles only `legacy` and `vendor`, so the branch is decided by
# the common include it sources, and the kernel branch is decided later still by
# a chain of numbered hooks. Anyone bumping this repo's pin should run this
# rather than trust a number copied from a previous investigation.
#
# What this script asserts, and what it deliberately does not:
#
#   GATING   the board -> family mapping; the family config still delegating the
#            branch to the common include; KERNEL_MAJOR_MINOR / LINUXFAMILY /
#            LINUXCONFIG on the branch's own arm; the kernel config file existing
#            at the pinned revision; and the KERNELBRANCH / KERNELSOURCE that
#            Armbian's hook chain actually settles on.
#
#   INFO     each board's KERNEL_TARGET. That list is Armbian's own board menu.
#            CeraLive builds KERNEL_TAG from source through the image pipeline
#            and never asks that menu, so a branch missing from it costs us
#            nothing — see kernel-pin.env note (ii). Printed, never gated.
#
# Read-only. Never edits kernel-pin.env; it prints what it found and exits
# non-zero on a mismatch so CI can fail on it.
#
# Usage:
#   scripts/preflight.sh              # check against the pinned ARMBIAN_BUILD_REV
#   scripts/preflight.sh --head       # check against armbian/build's CURRENT main
#
# `--head` is the one that matters when deciding to bump: it answers "has Armbian
# moved this branch since we pinned?".

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
echo "pinned branch: ${ARMBIAN_BRANCH}"
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

	# INFORMATIONAL — always passes. See the header note and kernel-pin.env (ii).
	if [[ ",${targets}," == *",${ARMBIAN_BRANCH},"* ]]; then
		note="lists ${ARMBIAN_BRANCH}"
	else
		note="does NOT list ${ARMBIAN_BRANCH}; non-gating, we build from source"
	fi
	printf '  info  %-26s KERNEL_TARGET=%s (%s)\n' "${board} branch menu" "${targets}" "${note}"
done

# --- does the family config still delegate the branch to the common include? --
echo
echo "Family config delegation"
if grep -qE "^[[:space:]]*${ARMBIAN_BRANCH}\)" "${tmp}/rockchip-rk3588.conf"; then
	echo "  DRIFT rockchip-rk3588.conf now handles '${ARMBIAN_BRANCH}' itself." >&2
	echo "        kernel-pin.env's derivation assumes it does NOT. Re-read it." >&2
	status=1
else
	echo "  ok    rockchip-rk3588.conf has no ${ARMBIAN_BRANCH}) case; rockchip64_common.inc decides"
fi

# --- the actual mapping ------------------------------------------------------
echo
echo "BRANCH=${ARMBIAN_BRANCH} mapping (rockchip64_common.inc)"
branch_block="$(awk -v b="${ARMBIAN_BRANCH}" \
	'$0 ~ "^[[:space:]]*" b "\\)" {f=1} f{print} f&&/;;/{exit}' \
	"${tmp}/rockchip64_common.inc")"
if [[ -z "${branch_block}" ]]; then
	echo "  DRIFT rockchip64_common.inc has no ${ARMBIAN_BRANCH}) arm at ${rev}." >&2
	echo "        Every value below is derived from it. Re-read the include." >&2
	status=1
fi
mm="$(sed -n 's/.*KERNEL_MAJOR_MINOR="\([^"]*\)".*/\1/p' <<<"${branch_block}" | head -1)"
lf="$(sed -n 's/.*LINUXFAMILY=\([A-Za-z0-9_]*\).*/\1/p'  <<<"${branch_block}" | head -1)"
check "KERNEL_MAJOR_MINOR" "${KERNEL_MAJOR_MINOR}" "${mm}"
check "LINUXFAMILY"        "${LINUXFAMILY}"        "${lf}"

# LINUXCONFIG is an INTERPOLATION — `'linux-rockchip64-'$BRANCH` — so the literal
# sitting in the file is not the config name. Expand $BRANCH the way Armbian
# would before comparing, otherwise this check can never match.
lc="$(sed -n 's/.*LINUXCONFIG=\(.*\)/\1/p' <<<"${branch_block}" | head -1)"
lc="${lc//\'/}"
lc="${lc%%[[:space:]]*}"
lc="${lc//\$\{BRANCH\}/${ARMBIAN_BRANCH}}"
lc="${lc//\$BRANCH/${ARMBIAN_BRANCH}}"
want_lc="$(basename "${KERNEL_CONFIG_SOURCE}" .config)"
check "LINUXCONFIG" "${want_lc}" "${lc}"

# A derived config name that names no file is a silent build failure downstream,
# so prove the file is really there at this revision rather than inferring it.
code="$(curl -sSL -o /dev/null -w '%{http_code}' "${RAW}/${rev}/${KERNEL_CONFIG_SOURCE}" || true)"
if [[ "${code}" == "200" ]]; then
	printf '  ok    %-26s %s\n' "config file present" "${KERNEL_CONFIG_SOURCE}"
else
	printf '  DRIFT %-26s %s missing at %s (HTTP %s)\n' \
		"config file" "${KERNEL_CONFIG_SOURCE}" "${rev}" "${code:-000}" >&2
	status=1
fi

# --- kernel branch + source (mainline-kernel.conf.sh) ------------------------
#
# Armbian settles KERNELBRANCH through a chain of numbered hooks, each of which
# returns early if an earlier one already set it. An EXPLICIT arm for a given
# MAJOR.MINOR therefore makes the rolling `branch:linux-<mm>.y` default in
# `__900_defaults` unreachable for that version.
#
# This is why the override is read FIRST. An earlier revision of this script
# checked the rolling default first and treated the presence of an explicit arm
# as drift — correct while we tracked 7.1, which has no arm, but exactly wrong
# now that the pinned branch resolves THROUGH one. Comparing the pin against the
# default would report permanent, unfixable drift.
echo
echo "Kernel branch (mainline-kernel.conf.sh)"
override="$(awk -v mm="${KERNEL_MAJOR_MINOR}" '
	/^[[:space:]]*#/ { next }
	index($0, "KERNEL_MAJOR_MINOR}\" == \"" mm "\"") { f = 1; next }
	f && /declare -g KERNELBRANCH=/ { print; exit }
	' "${tmp}/mainline-kernel.conf.sh" |
	sed -n 's/.*KERNELBRANCH="\([^"]*\)".*/\1/p' | head -1)"

if [[ -n "${override}" ]]; then
	check "KERNELBRANCH (explicit)" "${KERNELBRANCH_ARMBIAN}" "${override}"
elif grep -q 'KERNELBRANCH="branch:linux-${KERNEL_MAJOR_MINOR}.y"' \
	"${tmp}/mainline-kernel.conf.sh"; then
	# No arm for this MAJOR.MINOR, so the last-resort hook decides.
	check "KERNELBRANCH (default)" "${KERNELBRANCH_ARMBIAN}" "branch:linux-${mm}.y"
else
	echo "  DRIFT no explicit ${KERNEL_MAJOR_MINOR} arm, and __900_defaults no longer" >&2
	echo "        derives branch:linux-<mm>.y. The hook chain changed shape." >&2
	status=1
fi

# The source redirect is keyed on the branch VALUE the hook above settled on,
# not on MAJOR.MINOR, so it is looked up by that string.
src_override="$(awk -v kb="${KERNELBRANCH_ARMBIAN}" '
	/^[[:space:]]*#/ { next }
	index($0, "KERNELBRANCH}\" == ") && index($0, kb) { f = 1; next }
	f && /declare -g KERNELSOURCE=/ { print; exit }
	' "${tmp}/mainline-kernel.conf.sh" |
	sed -n 's/.*KERNELSOURCE="\([^"]*\)".*/\1/p' | head -1)"

if [[ -n "${src_override}" ]]; then
	check "KERNELSOURCE override" "${KERNELSOURCE_ARMBIAN:-}" "${src_override}"
elif [[ -n "${KERNELSOURCE_ARMBIAN:-}" ]]; then
	printf '  DRIFT %-26s pinned=%s  actual=no hook keyed on %s\n' \
		"KERNELSOURCE override" "${KERNELSOURCE_ARMBIAN}" "${KERNELBRANCH_ARMBIAN}" >&2
	status=1
else
	printf '  ok    %-26s %s\n' "KERNELSOURCE override" "none; mainline default applies"
fi

# --- what WE pin, for the reader -------------------------------------------
#
# Never gated here: this repo pins a FINAL tag on purpose while Armbian may sit
# on a release candidate. apply.sh is what proves the tag resolves.
echo
echo "This repository's pin (informational; apply.sh verifies it)"
printf '  info  %-26s %s\n' "KERNEL_TAG"        "${KERNEL_TAG}"
printf '  info  %-26s %s\n' "KERNEL_COMMIT"     "${KERNEL_COMMIT}"
printf '  info  %-26s %s\n' "KERNEL_PATCHDIR"   "${KERNEL_PATCHDIR}"
printf '  info  %-26s %s\n' "Armbian would use" "${KERNELBRANCH_ARMBIAN}"

echo
if (( status == 0 )); then
	echo "PREFLIGHT OK — kernel-pin.env matches armbian/build @ ${rev}"
else
	echo "PREFLIGHT DRIFT — kernel-pin.env is stale for armbian/build @ ${rev}" >&2
	echo "Update kernel-pin.env and docs/PREFLIGHT.md together, then re-run." >&2
fi
exit "${status}"
