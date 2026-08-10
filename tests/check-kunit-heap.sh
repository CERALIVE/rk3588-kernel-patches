#!/usr/bin/env bash
#
# check-kunit-heap.sh — read the ceralive_system_heap_test KUnit result out of
# the kernel log and prove the dma-heap partial-registration behaviour is what
# the driver claims.
#
# WHAT IS ACTUALLY BEING ASSERTED. At this kernel version dma_heap_add() has NO
# counterpart: there is no unregister, no rollback and no atomic pair-add. So a
# second registration that fails leaves the FIRST heap registered, permanently,
# for that boot. That is not a bug to be papered over with a fake rollback -- it
# is the honest behaviour of the API, and the KUnit case exists to pin it:
# with an injected failing add function, the first heap must remain and the
# initialisation must report the failure truthfully.
#
# The case drives an INJECTED add function, so it never registers or removes a
# real heap. This script therefore also asserts the boot's actual heaps are
# untouched -- a test that quietly consumed the system heap would pass its own
# TAP assertions while breaking the encoder.
#
# TAP is parsed strictly. `ok 1 - ...` and `not ok 1 - ...` differ by a prefix,
# so a substring search for "ok" matches a FAILURE; the match here is anchored.
# A missing result is a failure too: a suite that did not run proves nothing, and
# an absent line is exactly what a kernel built without the symbol produces.
#
# Usage:
#   journalctl -k -b -o cat | check-kunit-heap.sh --journal -
#   check-kunit-heap.sh --journal /path/to/kernel.log
#   check-kunit-heap.sh --self-test        # host-side, no hardware, no root

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/qa-common.sh
source "${HERE}/lib/qa-common.sh"

QA_SUITE="ceralive_system_heap_test"
QA_JOURNAL=""
QA_HEAP_DIR="${QA_HEAP_DIR:-/dev/dma_heap}"

usage() { sed -n '2,29p' "${BASH_SOURCE[0]}"; }

# check_tap <file>
#
# KUnit prints a per-suite TAP block. The suite line is what decides, and both
# spellings the kernel has used ("ok <n> - <suite>" and "ok <n> <suite>") are
# accepted so a KUnit formatting change does not read as a driver regression.
check_tap() {
	local log="$1" pass fail

	pass="$(grep -cE "^[[:space:]]*ok [0-9]+ (- )?${QA_SUITE}\b" "${log}")"
	fail="$(grep -cE "^[[:space:]]*not ok [0-9]+ (- )?${QA_SUITE}\b" "${log}")"

	if (( fail > 0 )); then
		qa_fail "${QA_SUITE}: KUnit reported ${fail} failing result(s)"
		grep -E "^[[:space:]]*not ok .*${QA_SUITE}" "${log}" >&2
		return 1
	fi
	if (( pass == 0 )); then
		qa_fail "${QA_SUITE}: no KUnit result in the log at all — the suite did not run (is CONFIG_DMABUF_HEAPS_CERALIVE_TEST set?)"
		return 1
	fi
	qa_log "ok ${QA_SUITE}: ${pass} passing KUnit result(s), zero failures"
	return 0
}

# The test must not alter the boot's real heaps. `system` is what everything
# falls back to and `system-uncached` is what the Rockchip MPP encoder opens by
# hard-coded name, so both are asserted by name rather than by count.
check_real_heaps_intact() {
	local heap
	if [[ ! -d "${QA_HEAP_DIR}" ]]; then
		qa_warn "${QA_HEAP_DIR} absent — skipping the real-heap assertion (host run?)"
		return 0
	fi
	for heap in system system-uncached; do
		if [[ -e "${QA_HEAP_DIR}/${heap}" ]]; then
			qa_log "ok real heap still present: ${heap}"
		else
			qa_fail "real heap MISSING after the KUnit run: ${heap}"
		fi
	done
}

run_self_test() {
	local rc=0 work
	work="$(mktemp -d)"
	QA_HEAP_DIR="${work}/absent-heaps"

	printf 'ok 1 - %s\n' "${QA_SUITE}" >"${work}/pass.log"
	QA_FAILURES=0
	check_tap "${work}/pass.log" >/dev/null 2>&1
	if (( QA_FAILURES == 0 )); then
		printf '  ok  a passing TAP result is accepted\n'
	else
		printf '  FAIL a passing TAP result was rejected\n' >&2; rc=1
	fi

	# The trap this anchoring exists for: "not ok 1 - <suite>" CONTAINS
	# "ok 1 - <suite>", so an unanchored grep reports a failure as a pass.
	printf 'not ok 1 - %s\n' "${QA_SUITE}" >"${work}/fail.log"
	QA_FAILURES=0
	check_tap "${work}/fail.log" >/dev/null 2>&1
	if (( QA_FAILURES > 0 )); then
		printf '  ok  a FAILING TAP result is rejected (not-ok is not read as ok)\n'
	else
		printf '  FAIL a failing TAP result was accepted\n' >&2; rc=1
	fi

	printf 'some unrelated kernel line\n' >"${work}/empty.log"
	QA_FAILURES=0
	check_tap "${work}/empty.log" >/dev/null 2>&1
	if (( QA_FAILURES > 0 )); then
		printf '  ok  a MISSING result is rejected (a suite that did not run proves nothing)\n'
	else
		printf '  FAIL a missing result was accepted\n' >&2; rc=1
	fi

	printf 'ok 3 %s\n' "${QA_SUITE}" >"${work}/nodash.log"
	QA_FAILURES=0
	check_tap "${work}/nodash.log" >/dev/null 2>&1
	if (( QA_FAILURES == 0 )); then
		printf '  ok  the dashless TAP spelling is also accepted\n'
	else
		printf '  FAIL the dashless TAP spelling was rejected\n' >&2; rc=1
	fi

	QA_HEAP_DIR="${work}/heaps"
	mkdir -p "${QA_HEAP_DIR}"; : >"${QA_HEAP_DIR}/system"
	QA_FAILURES=0
	check_real_heaps_intact >/dev/null 2>&1
	if (( QA_FAILURES > 0 )); then
		printf '  ok  a missing real heap is reported as a FAILURE\n'
	else
		printf '  FAIL a missing real heap passed\n' >&2; rc=1
	fi

	rm -rf "${work}"
	(( rc == 0 )) && printf 'RESULT=PASS case=self-test\n'
	return "${rc}"
}

main() {
	local self_test=0

	while (( $# )); do
		case "$1" in
			--journal)   QA_JOURNAL="${2:-}"; shift 2 ;;
			--journal=*) QA_JOURNAL="${1#--journal=}"; shift ;;
			--suite)     QA_SUITE="${2:-}"; shift 2 ;;
			--suite=*)   QA_SUITE="${1#--suite=}"; shift ;;
			--self-test) self_test=1; shift ;;
			-h|--help)   usage; return 0 ;;
			*) usage >&2; qa_die "unknown argument: $1" ;;
		esac
	done

	(( self_test )) && { run_self_test; return $?; }

	[[ -n "${QA_JOURNAL}" ]] || { usage >&2; qa_die "--journal <file|-> is required"; }

	local log
	log="$(mktemp)"
	if [[ "${QA_JOURNAL}" == "-" ]]; then
		cat >"${log}"
	else
		[[ -r "${QA_JOURNAL}" ]] || qa_die "journal not readable: ${QA_JOURNAL}"
		cat "${QA_JOURNAL}" >"${log}"
	fi

	check_tap "${log}"
	check_real_heaps_intact
	rm -f "${log}"

	qa_result "kunit-heap" "suite=${QA_SUITE}"
}

main "$@"
