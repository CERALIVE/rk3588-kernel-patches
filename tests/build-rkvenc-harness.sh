#!/usr/bin/env bash
#
# build-rkvenc-harness.sh — cross-compile tests/rkvenc-invalid-ioctl.c against
# the UAPI of a VERIFIED applied kernel tree.
#
# WHY --kernel-tree IS MANDATORY. This repository is patches only: it carries no
# kernel source, so the harness has no in-tree UAPI to compile against. The
# tempting alternatives are both wrong. Vendoring a copy of rkvenc.h here would
# let the harness drift from the series it is supposed to test, silently, and
# exactly at the moment the series changes the interface. Letting this script
# fetch and apply its own tree would mean the harness is built against a tree
# nobody reviewed.
#
# So the tree is an INPUT, and it is VALIDATED BEFORE ANY COMPILATION:
#
#   1. the base commit is the pinned KERNEL_COMMIT from kernel-pin.env;
#   2. the full series is applied -- the git log subjects above that base equal
#      patches/series, in order, with nothing missing and nothing extra.
#
# Produce one with:  scripts/apply.sh --keep /abs/path/to/tree
#
# A tree that fails either check fails HERE, before the compiler is invoked, so
# "the harness built" can never mean "the harness built against something else".
#
# Usage:
#   build-rkvenc-harness.sh --kernel-tree <abs path> [--out <dir>]
#   build-rkvenc-harness.sh --self-test        # host-side, no tree needed

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${HERE}/.." && pwd)"
SOURCE="${HERE}/rkvenc-invalid-ioctl.c"
TABLE="${HERE}/expected-errno.tsv"

KERNEL_TREE=""
OUT_DIR="${ROOT}/.work/harness"
CC="${CC:-aarch64-linux-gnu-gcc}"

die() { printf 'build-rkvenc-harness: %s\n' "$*" >&2; exit 2; }
log() { printf '  %s\n' "$*"; }

usage() { sed -n '2,29p' "${BASH_SOURCE[0]}"; }

# ---------------------------------------------------------------------------
# Tree validation — the whole point of the mandatory argument.
# ---------------------------------------------------------------------------

series_subjects() {
	# `git am` writes each patch's Subject as the commit subject with the
	# [PATCH n/m] prefix stripped, so the series' own subjects are what the
	# log must show. Read them out of patches/ rather than re-deriving them.
	local name
	while read -r name; do
		[[ -n "${name}" && "${name}" != \#* ]] || continue
		sed -n 's/^Subject: \[PATCH [0-9]*\/[0-9]*\] //p' \
			"${ROOT}/patches/${name}" | head -1
	done <"${ROOT}/patches/series"
}

validate_tree() {
	local tree="$1" pinned base applied expected

	[[ -d "${tree}/.git" ]] || die "not a git tree: ${tree}"

	# shellcheck source=../kernel-pin.env
	source "${ROOT}/kernel-pin.env"
	pinned="${KERNEL_COMMIT}"

	mapfile -t expected < <(series_subjects)
	(( ${#expected[@]} > 0 )) || die "patches/series produced no subjects"

	mapfile -t applied < <(git -C "${tree}" log --format=%s -n "${#expected[@]}" HEAD |
		tac)
	(( ${#applied[@]} == ${#expected[@]} )) \
		|| die "tree has fewer than ${#expected[@]} commits above its base"

	base="$(git -C "${tree}" rev-parse "HEAD~${#expected[@]}" 2>/dev/null)" \
		|| die "cannot resolve the tree's base commit"
	[[ "${base}" == "${pinned}" ]] \
		|| die "tree base is ${base}, but kernel-pin.env pins ${pinned} — this is not the pinned kernel"

	local i
	for (( i = 0; i < ${#expected[@]}; i++ )); do
		[[ "${applied[i]}" == "${expected[i]}" ]] \
			|| die "series mismatch at position $(( i + 1 )): tree has '${applied[i]}', patches/series expects '${expected[i]}'"
	done

	log "verified ${tree}: base ${base}, all ${#expected[@]} series patches applied in order"
}

# ---------------------------------------------------------------------------
# UAPI include path
#
# The raw include/uapi tree is NOT directly compilable from userspace -- it
# still carries __user annotations and the kernel-headers warning -- so the
# GENERATED, exported headers are used when they can be produced, and the raw
# tree is the documented fallback with the two kernel-only spellings defined
# away. Both are passed, generated first.
# ---------------------------------------------------------------------------

resolve_includes() {
	local tree="$1" gen="${OUT_DIR}/uapi"
	local -a inc=()

	rm -rf "${gen}"
	if make -C "${tree}" ARCH=arm64 headers_install \
		INSTALL_HDR_PATH="${gen}" >/dev/null 2>&1 && \
		[[ -f "${gen}/include/linux/rkvenc.h" ]]; then
		inc+=(-I "${gen}/include")
		# stderr, NOT stdout: the caller reads this function's stdout as
		# the include list, so a log line here becomes a compiler flag.
		log "using the generated UAPI at ${gen}/include" >&2
	else
		log "headers_install unavailable; falling back to the raw uapi tree" >&2
		inc+=(-D__EXPORTED_HEADERS__ '-D__user=')
	fi
	inc+=(-I "${tree}/include/uapi")

	printf '%s\n' "${inc[@]}"
}

# ---------------------------------------------------------------------------
# Expectation-table fixture — validated on the HOST, before anything is copied
# to a board. A malformed table discovered mid-drill is a wasted board session.
# ---------------------------------------------------------------------------

validate_table() {
	local table="$1" rc=0
	local -A seen=()
	local line name err what lineno=0 rows=0

	[[ -r "${table}" ]] || die "expectation table not readable: ${table}"

	while IFS= read -r line; do
		lineno=$(( lineno + 1 ))
		[[ -n "${line}" && "${line}" != \#* ]] || continue
		IFS=$'\t' read -r name err what <<<"${line}"
		[[ "${name}" == "case" ]] && continue

		if [[ -z "${name}" || -z "${err}" || -z "${what}" ]]; then
			printf '  FAIL %s:%d: expected three tab-separated columns\n' \
				"${table}" "${lineno}" >&2
			rc=1
			continue
		fi
		if [[ ! "${name}" =~ ^[a-z0-9-]+$ ]]; then
			printf '  FAIL %s:%d: case name %q is not [a-z0-9-]+\n' \
				"${table}" "${lineno}" "${name}" >&2
			rc=1
		fi
		case "${err}" in
			OK|EINVAL|EFAULT|ENOMEM|ENODEV|EBUSY|EIO) ;;
			*) printf '  FAIL %s:%d: unknown errno name %q\n' \
				"${table}" "${lineno}" "${err}" >&2; rc=1 ;;
		esac
		if [[ -n "${seen[${name}]:-}" ]]; then
			printf '  FAIL %s:%d: duplicate case %q\n' \
				"${table}" "${lineno}" "${name}" >&2
			rc=1
		fi
		seen["${name}"]=1
		rows=$(( rows + 1 ))
	done <"${table}"

	if (( rows == 0 )); then
		printf '  FAIL %s declares no cases\n' "${table}" >&2
		rc=1
	fi

	# Every case the harness can run must have a row, and every row must name
	# a case the harness can run. A row with no case is an expectation nobody
	# checks; a case with no row is a case that expects nothing.
	local c
	while read -r c; do
		[[ -n "${seen[${c}]:-}" ]] || {
			printf '  FAIL harness case %q has no row in %s\n' "${c}" "${table}" >&2
			rc=1
		}
	done < <(grep -oE 'run_case\("[a-z0-9-]+"' "${SOURCE}" |
		sed 's/run_case("//; s/"//' | sort -u)

	(( rc == 0 )) && log "expectation table validated: ${rows} case(s)"
	return "${rc}"
}

run_self_test() {
	local rc=0 work
	work="$(mktemp -d)"

	if validate_table "${TABLE}" >/dev/null 2>&1; then
		printf '  ok  the shipped expectation table validates\n'
	else
		printf '  FAIL the shipped expectation table does not validate\n' >&2
		rc=1
	fi

	printf 'dup\tEINVAL\tone\ndup\tEINVAL\ttwo\n' >"${work}/dup.tsv"
	if validate_table "${work}/dup.tsv" >/dev/null 2>&1; then
		printf '  FAIL a duplicate case was accepted\n' >&2; rc=1
	else
		printf '  ok  a duplicate case is rejected\n'
	fi

	printf 'x\tENOSUCH\tone\n' >"${work}/unknown.tsv"
	if validate_table "${work}/unknown.tsv" >/dev/null 2>&1; then
		printf '  FAIL an unknown errno name was accepted\n' >&2; rc=1
	else
		printf '  ok  an unknown errno name is rejected\n'
	fi

	printf 'x\tEINVAL\n' >"${work}/short.tsv"
	if validate_table "${work}/short.tsv" >/dev/null 2>&1; then
		printf '  FAIL a malformed row was accepted\n' >&2; rc=1
	else
		printf '  ok  a malformed row is rejected\n'
	fi

	: >"${work}/empty.tsv"
	if validate_table "${work}/empty.tsv" >/dev/null 2>&1; then
		printf '  FAIL an empty table was accepted\n' >&2; rc=1
	else
		printf '  ok  an empty table is rejected\n'
	fi

	# A table that omits a case the harness actually runs must fail: an
	# unexpected case is a case whose result nobody is checking.
	grep -v '^offset-size-wrap' "${TABLE}" >"${work}/missing.tsv"
	if validate_table "${work}/missing.tsv" >/dev/null 2>&1; then
		printf '  FAIL a table missing a harness case was accepted\n' >&2; rc=1
	else
		printf '  ok  a table missing a harness case is rejected\n'
	fi

	# An unvalidated or absent tree must fail BEFORE the compiler runs.
	if ( validate_tree "${work}/not-a-tree" ) >/dev/null 2>&1; then
		printf '  FAIL a non-git path was accepted as a kernel tree\n' >&2; rc=1
	else
		printf '  ok  a non-git path is refused as a kernel tree\n'
	fi

	git -C "${work}" init -q 2>/dev/null
	git -C "${work}" -c user.name=t -c user.email=t@t commit -q --allow-empty \
		-m 'not the pinned base' 2>/dev/null
	if ( validate_tree "${work}" ) >/dev/null 2>&1; then
		printf '  FAIL a tree at the wrong base was accepted\n' >&2; rc=1
	else
		printf '  ok  a tree at the wrong base is refused\n'
	fi

	if command -v "${CC}" >/dev/null 2>&1; then
		printf '  ok  cross compiler present: %s\n' "${CC}"
	else
		printf '  WARN cross compiler %s absent; a real build would fail here\n' "${CC}"
	fi

	rm -rf "${work}"
	(( rc == 0 )) && printf 'RESULT=PASS case=build-harness-self-test\n'
	return "${rc}"
}

main() {
	local self_test=0

	while (( $# )); do
		case "$1" in
			--kernel-tree)   KERNEL_TREE="${2:-}"; shift 2 ;;
			--kernel-tree=*) KERNEL_TREE="${1#--kernel-tree=}"; shift ;;
			--out)           OUT_DIR="${2:-}"; shift 2 ;;
			--out=*)         OUT_DIR="${1#--out=}"; shift ;;
			--self-test)     self_test=1; shift ;;
			-h|--help)       usage; return 0 ;;
			*) usage >&2; die "unknown argument: $1" ;;
		esac
	done

	(( self_test )) && { run_self_test; return $?; }

	[[ -n "${KERNEL_TREE}" ]] \
		|| { usage >&2; die "--kernel-tree is MANDATORY (produce one with scripts/apply.sh --keep <dir>)"; }
	[[ -d "${KERNEL_TREE}" ]] || die "no such kernel tree: ${KERNEL_TREE}"
	command -v "${CC}" >/dev/null 2>&1 || die "cross compiler not found: ${CC}"

	mkdir -p "${OUT_DIR}"

	# Validate FIRST. Nothing is compiled against an unverified tree.
	validate_tree "${KERNEL_TREE}"
	validate_table "${TABLE}" || die "the expectation table is invalid; refusing to build a harness that would assert nothing"

	local -a includes
	mapfile -t includes < <(resolve_includes "${KERNEL_TREE}")

	"${CC}" -O2 -Wall -Wextra -Werror "${includes[@]}" \
		"${SOURCE}" -o "${OUT_DIR}/rkvenc-invalid-ioctl" \
		|| die "harness compilation failed"

	cp "${TABLE}" "${OUT_DIR}/expected-errno.tsv"

	log "built ${OUT_DIR}/rkvenc-invalid-ioctl"
	log "beside it: ${OUT_DIR}/expected-errno.tsv"
	printf 'RESULT=PASS case=build-rkvenc-harness tree=%s out=%s\n' \
		"${KERNEL_TREE}" "${OUT_DIR}"
}

main "$@"
