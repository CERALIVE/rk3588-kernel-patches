#!/usr/bin/env bash
#
# preflight.sh — validate CeraLive's sovereign kernel pin and, optionally,
# report how a selected Armbian mapping currently resolves.
#
# Armbian is an informational source only. Its branch aliases never decide
# whether this repository's push or pull-request gate passes.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${HERE}/.." && pwd)"

# shellcheck source=../kernel-pin.env
source "${ROOT}/kernel-pin.env"

status=0
fail() {
	echo "  FAIL $*" >&2
	status=1
}

echo "CeraLive kernel pin preflight"
echo

for required in KERNEL_TAG KERNEL_COMMIT KERNEL_PATCHDIR KERNELSOURCE; do
	[[ -n "${!required:-}" ]] || fail "${required} is not set in kernel-pin.env"
done

if [[ -n "${KERNEL_TAG:-}" ]]; then
	tag_version="${KERNEL_TAG#v}"
	if [[ ! "${KERNEL_TAG}" =~ ^v[0-9]+\.[0-9]+$ ]]; then
		fail "KERNEL_TAG has invalid upstream-style version: ${KERNEL_TAG}"
	fi
	if [[ "${KERNEL_PATCHDIR:-}" != "patch/kernel/archive/rockchip64-${tag_version}" ]]; then
		fail "KERNEL_PATCHDIR ${KERNEL_PATCHDIR:-<unset>} is inconsistent with KERNEL_TAG ${KERNEL_TAG}"
	fi
fi

if [[ ! "${KERNEL_COMMIT:-}" =~ ^[0-9a-f]{40}$ ]]; then
	fail "KERNEL_COMMIT is not a 40-character commit SHA"
fi

# Resolve the sovereign pin from its own source remote. This does not consult
# Armbian and catches a deleted, moved, or mistyped KERNEL_COMMIT.
if [[ -n "${KERNELSOURCE:-}" && "${KERNEL_COMMIT:-}" =~ ^[0-9a-f]{40}$ && -n "${KERNEL_TAG:-}" ]]; then
	refs="$(git ls-remote "${KERNELSOURCE}" "refs/tags/${KERNEL_TAG}" "refs/tags/${KERNEL_TAG}^{}" 2>/dev/null || true)"
	resolved="$(awk '$2 == "refs/tags/'"${KERNEL_TAG}"'^{}" { print $1; exit }' <<<"${refs}")"
	if [[ -z "${resolved}" ]]; then
		resolved="$(awk '$2 == "refs/tags/'"${KERNEL_TAG}"'" { print $1; exit }' <<<"${refs}")"
	fi
	if [[ "${resolved}" == "${KERNEL_COMMIT}" ]]; then
		echo "  ok    ${KERNEL_TAG} resolves to ${KERNEL_COMMIT} from ${KERNELSOURCE}"
	else
		fail "${KERNEL_TAG} resolves to ${resolved:-<missing>} from ${KERNELSOURCE}, expected ${KERNEL_COMMIT}"
	fi
fi

echo
echo "CeraLive pin"
printf '  info  %-18s %s\n' "KERNEL_TAG" "${KERNEL_TAG:-<unset>}"
printf '  info  %-18s %s\n' "KERNEL_COMMIT" "${KERNEL_COMMIT:-<unset>}"
printf '  info  %-18s %s\n' "KERNEL_PATCHDIR" "${KERNEL_PATCHDIR:-<unset>}"

armbian_revision="${ARMBIAN_BUILD_REV:-}"
if [[ "${1:-}" == "--head" && -n "${ARMBIAN_BRANCH:-}" ]]; then
	armbian_revision="$(curl -fsSL "https://api.github.com/repos/armbian/build/commits/main" 2>/dev/null |
		sed -n 's/.*"sha": *"\([0-9a-f]\{40\}\)".*/\1/p' | head -1 || true)"
fi

# The selected Armbian alias is deliberately optional and informational. No
# result from this block changes status, including fetch or mapping failures.
if [[ -n "${armbian_revision}" && -n "${ARMBIAN_BRANCH:-}" ]]; then
	RAW="https://raw.githubusercontent.com/armbian/build"
	tmp="$(mktemp -d)"
	trap 'rm -rf "${tmp}"' EXIT
	fetch_info() {
		local path="$1"
		if curl -fsSL "${RAW}/${armbian_revision}/${path}" -o "${tmp}/$(basename "${path}")"; then
			return 0
		fi
		echo "  info  Armbian ${path}: unavailable at ${armbian_revision}" >&2
		return 1
	}

	echo
	echo "Armbian mapping (informational; alias=${ARMBIAN_BRANCH}, revision=${armbian_revision})"
	if fetch_info config/sources/families/include/rockchip64_common.inc; then
		block="$(awk -v b="${ARMBIAN_BRANCH}" '$0 ~ "^[[:space:]]*" b "\\)" { f=1 } f { print } f && /;;/ { exit }' "${tmp}/rockchip64_common.inc")"
		mm="$(sed -n 's/.*KERNEL_MAJOR_MINOR="\([^"]*\)".*/\1/p' <<<"${block}" | head -1)"
		lf="$(sed -n 's/.*LINUXFAMILY=\([A-Za-z0-9_]*\).*/\1/p' <<<"${block}" | head -1)"
		printf '  info  %-18s %s\n' "KERNEL_MAJOR_MINOR" "${mm:-<unresolved>}"
		printf '  info  %-18s %s\n' "LINUXFAMILY" "${lf:-<unresolved>}"
	else
		echo "  info  Armbian alias mapping unavailable"
	fi
	if fetch_info config/sources/mainline-kernel.conf.sh; then
		printf '  info  %-18s Armbian hook file fetched\n' "KERNELBRANCH"
	else
		echo "  info  Armbian kernel-branch hook unavailable"
	fi
else
	echo
	echo "Armbian mapping: not configured (informational source disabled)"
fi

echo
if (( status == 0 )); then
	echo "PREFLIGHT OK — CeraLive sovereign kernel pin is internally consistent"
else
	echo "PREFLIGHT FAIL — CeraLive sovereign kernel pin needs repair" >&2
fi
exit "${status}"
