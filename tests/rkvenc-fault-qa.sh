#!/usr/bin/env bash
#
# rkvenc-fault-qa.sh — force one rkvenc negative path on a real board and prove
# the driver handled it.
#
# RUNS ON HARDWARE ONLY, on the non-shipping `edge-test` kernel (KASAN +
# lockdep + CONFIG_VIDEO_ROCKCHIP_RKVENC_CERALIVE_TEST). Every case follows the
# same four steps, and the ORDER is the point:
#
#   1. arm the one-shot knob and record its consumed counter;
#   2. perform the operation that must hit it;
#   3. assert the EXPECTED ERRNO, then assert the counter incremented by exactly
#      one and the knob reset itself -- a driver that ignored the knob would
#      otherwise give a clean run and a green transcript;
#   4. assert the device still works: no sanitizer/lockdep report, and a real
#      60-frame hardware encode that produces bytes.
#
# Step 4 is not decoration. Every fix in this series is about the state left
# behind by a failure, so "the error came back" is at most half the claim.
#
# Usage:
#   rkvenc-fault-qa.sh --case <name> [--delay-ms N]
#                      [--debugfs /sys/kernel/debug/rkvenc-test]
#                      [--device /dev/mpp_service]
#   rkvenc-fault-qa.sh --self-test        # host-side, no hardware, no root
#
# Cases: fail-service-attach fail-ccu-attach fail-irq-request
#        fail-clock-enable delayed-teardown

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/qa-common.sh
source "${HERE}/lib/qa-common.sh"
# shellcheck source=lib/qa-fixture.sh
source "${HERE}/lib/qa-fixture.sh"

# shellcheck disable=SC2034  # read by lib/qa-common.sh to pick this driver's control table
QA_DRIVER=rkvenc
QA_DEBUGFS="/sys/kernel/debug/rkvenc-test"
QA_DEVICE="/dev/mpp_service"
QA_CASE=""
QA_DELAY_MS=2500
QA_DRIVER_DIR="${QA_DRIVER_DIR:-/sys/bus/platform/drivers/rkvenc}"
QA_UNBIND_TIMEOUT="${QA_UNBIND_TIMEOUT:-15}"

usage() { sed -n '2,28p' "${BASH_SOURCE[0]}"; }

# ---------------------------------------------------------------------------
# Device discovery — never hardcode a platform address.
#
# fdbd0000/fdbe0000 are RK3588 facts, not driver facts; a board respin or a DT
# change moves them and a hardcoded path would silently select nothing, which
# reads exactly like a pass.
# ---------------------------------------------------------------------------

qa_core_devices() {
	local link name
	for link in "${QA_DRIVER_DIR}"/*; do
		[[ -L "${link}" ]] || continue
		name="$(basename "${link}")"
		case "${name}" in *rkvenc-core*|*rkvenc_core*) printf '%s\n' "${name}" ;; esac
	done
}

qa_first_core() {
	local first
	first="$(qa_core_devices | head -1)"
	[[ -n "${first}" ]] || qa_die "no rkvenc core device bound under ${QA_DRIVER_DIR}"
	printf '%s' "${first}"
}

# qa_bind_expect_errno <device> <expected-errno-name>
#
# The kernel reports a probe failure as the errno of the write(2) to `bind`, so
# the assertion is on the write. What the write RETURNS is an errno; what the
# shell PRINTS is a strerror sentence, and the two never look alike — the
# assertion therefore goes through qa_write_expect_errno, which prefers the raw
# syscall errno and falls back to a full symbol/strerror mapping.
qa_bind_expect_errno() {
	local dev="$1" want="$2"
	qa_write_expect_errno "${QA_DRIVER_DIR}/bind" "${dev}" "${want}" \
		"bind of ${dev}"
}

qa_unbind() {
	local dev="$1"
	timeout "${QA_UNBIND_TIMEOUT}" \
		sh -c "printf '%s' '${dev}' > '${QA_DRIVER_DIR}/unbind'" 2>/dev/null
}

qa_bind() {
	local dev="$1"
	timeout "${QA_UNBIND_TIMEOUT}" \
		sh -c "printf '%s' '${dev}' > '${QA_DRIVER_DIR}/bind'" 2>/dev/null
}

# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------

# A bind-time fault: unbind a core, arm, re-bind (which must fail with the
# documented errno), then re-bind cleanly and prove the encoder still works.
run_bind_fault_case() {
	local case_name="$1" knob="$2"
	local core mark errno

	errno="$(qa_errno_for "${knob}")"
	[[ -n "${errno}" ]] || qa_die "no expected errno registered for ${knob}"

	core="$(qa_first_core)"
	mark="$(qa_dmesg_mark)"

	qa_unbind "${core}" || qa_fail "could not unbind ${core}"
	qa_arm "${knob}" 1 || return 1
	qa_bind_expect_errno "${core}" "${errno}"
	qa_assert_consumed

	qa_bind "${core}" || qa_fail "clean re-bind of ${core} failed"
	if [[ -e "${QA_DEVICE}" ]]; then
		qa_log "ok ${QA_DEVICE} present after re-bind"
	else
		qa_fail "${QA_DEVICE} absent after re-bind"
	fi

	qa_assert_no_sanitizer_report "${mark}" "${case_name}"
	qa_encode "${case_name} post-fault"
	qa_result "${case_name}" "errno=${errno}" "core=${core}"
}

run_fail_clock_enable() {
	local mark
	mark="$(qa_dmesg_mark)"

	qa_arm fail_clock_enable_once 1 || return 1
	qa_encode_expect_failure "fail-clock-enable"
	qa_assert_consumed
	qa_assert_no_sanitizer_report "${mark}" "fail-clock-enable"

	# The whole point of the fix: a failed run leaves PM and clock counts
	# balanced, so the very next run must succeed with no intervening reset.
	qa_encode "fail-clock-enable recovery"
	qa_result "fail-clock-enable" "errno=EIO"
}

run_delayed_teardown() {
	local mark
	mark="$(qa_dmesg_mark)"

	qa_arm delay_task_completion_ms "${QA_DELAY_MS}" || return 1

	# The encode itself must still SUCCEED -- the delay stretches the window
	# between "task finished" and "session released", it does not break the
	# task. A failure here would mean the delay corrupted the task path
	# rather than merely widening a race.
	qa_encode "delayed-teardown"
	qa_assert_consumed
	qa_assert_no_sanitizer_report "${mark}" "delayed-teardown"
	qa_encode "delayed-teardown recovery"
	qa_result "delayed-teardown" "delay_ms=${QA_DELAY_MS}"
}

# ---------------------------------------------------------------------------
# Self-test — proves the harness itself is not vacuous, with no hardware.
# ---------------------------------------------------------------------------

check() {
	local ok="$1" what="$2"
	if (( ok )); then
		printf '  ok  %s\n' "${what}"
	else
		printf '  FAIL %s\n' "${what}" >&2
		SELFTEST_RC=1
	fi
}

# The three defects the FIRST real board run found, and which this self-test
# could not see because it built its fixture from the same assumptions the
# harness made. Each now has a case here that fails if it is reintroduced.
selftest_regressions() {
	local work="$1" out rc

	# (1) WRONG NODE NAMES. The table is checked against the driver source
	# itself, so the harness and the kernel cannot drift apart silently.
	QA_FAILURES=0
	qa_verify_controls_against_patches "${HERE}/.." >/dev/null 2>&1
	rc=$?
	case "${rc}" in
		0) check 1 "the fault-control table matches the driver sources in patches/" ;;
		77) printf '  WARN patches/ not present; the driver-source cross-check was skipped\n' >&2 ;;
		*) check 0 "the fault-control table matches the driver sources in patches/" ;;
	esac

	# The exact names the board proved real, spelled out rather than derived,
	# so a "tidy-up" of the table is a visible diff against reality.
	check "$([[ "$(QA_DRIVER=rkvenc qa_counter_for fail_service_attach_once)" == fail_service_attach_once_consumed ]] && echo 1 || echo 0)" \
		"rkvenc keeps the _once in its counter (fail_service_attach_once_consumed)"
	check "$([[ "$(QA_DRIVER=hdmirx qa_counter_for fail_clk_set_rate_once)" == fail_clk_set_rate_consumed ]] && echo 1 || echo 0)" \
		"hdmirx drops the _once in its counter (fail_clk_set_rate_consumed)"
	check "$([[ "$(QA_DRIVER=rkvenc qa_counter_for delay_task_completion_ms)" == delay_consumed ]] && echo 1 || echo 0)" \
		"the rkvenc delay knob's counter is delay_consumed, not <knob>_consumed"

	# (2) ERRNO MATCHED AGAINST THE WRONG STRING. The literal text the board
	# produced is the fixture: a symbol-grep cannot match it.
	local real='printf: write error: Cannot allocate memory'
	check "$(qa_errno_matches ENOMEM "${real}" && echo 1 || echo 0)" \
		"the board's real message is recognised as ENOMEM"
	if qa_errno_matches EIO "${real}"; then
		printf '  FAIL a mismatched errno was accepted\n' >&2; SELFTEST_RC=1
	else
		printf '  ok  a mismatched errno is rejected\n'
	fi
	check "$(qa_errno_matches ENODEV 'bash: line 1: printf: write error: No such device' && echo 1 || echo 0)" \
		"a multi-prefix diagnostic still yields its errno"
	# ENODEV's string is a PREFIX of ENXIO's, so a substring match would
	# confuse them; the phrase is compared whole for exactly this reason.
	if qa_errno_matches ENODEV 'sh: /sys/x: No such device or address'; then
		printf '  FAIL ENXIO was accepted as ENODEV\n' >&2; SELFTEST_RC=1
	else
		printf '  ok  ENXIO is not confused with ENODEV\n'
	fi
	check "$(qa_errno_matches EBUSY 'EBUSY' && echo 1 || echo 0)" \
		"a bare symbol is still accepted"
	check "$(qa_errno_matches ENOSPC '' 28 && echo 1 || echo 0)" \
		"a raw syscall errno number is authoritative"

	# The whole chain, against a REAL kernel write failure: /dev/full always
	# returns ENOSPC, so this proves the capture and the match together
	# without inventing either side.
	# Captured to a FILE, not through $(...): a command substitution runs in a
	# subshell, and qa_fail's count would not come back — the assertion would
	# then be the vacuous kind this whole file exists to prevent.
	out="${work}/enospc.log"
	QA_FAILURES=0
	qa_write_expect_errno /dev/full x ENOSPC 'write to /dev/full' >"${out}" 2>&1
	check "$([[ ${QA_FAILURES} -eq 0 ]] && echo 1 || echo 0)" \
		"a real ENOSPC from /dev/full is asserted end to end${QA_WRITE_ERRNO_BIN:+ (syscall helper)}"
	[[ ${QA_FAILURES} -eq 0 ]] || sed 's/^/       /' "${out}" >&2

	QA_FAILURES=0
	qa_write_expect_errno /dev/full x ENOMEM 'write to /dev/full' >/dev/null 2>&1
	check "$([[ ${QA_FAILURES} -gt 0 ]] && echo 1 || echo 0)" \
		"the wrong expected errno FAILS against that same real write"

	# (3) THE `ERR` SENTINEL UNDER set -u. An unreadable knob used to store
	# the literal `ERR`, which `$(( ERR + 1 ))` then dereferenced as a NAME,
	# aborting the harness mid-case with the device left unbound. The check
	# is that the harness RETURNS rather than dies, so it is run in a child
	# shell under the strict profile the board uses.
	if QA_SELFTEST_STRICT_DIR="${work}" bash -c '
		set -Eeuo pipefail
		source "'"${HERE}"'/lib/qa-common.sh"
		QA_DEBUGFS="${QA_SELFTEST_STRICT_DIR}/absent"
		QA_DRIVER=rkvenc
		qa_arm fail_service_attach_once 1 >/dev/null 2>&1 || true
		qa_assert_consumed >/dev/null 2>&1 || true
		printf reached
	' 2>/dev/null | grep -q reached; then
		printf '  ok  an unreadable knob does not abort the harness under set -u\n'
	else
		printf '  FAIL an unreadable knob still aborts under set -u\n' >&2
		SELFTEST_RC=1
	fi

	QA_FAILURES=0
	QA_DEBUGFS="${work}/absent"
	qa_arm fail_service_attach_once 1 >/dev/null 2>&1
	qa_assert_consumed >/dev/null 2>&1
	check "$([[ ${QA_FAILURES} -gt 0 ]] && echo 1 || echo 0)" \
		"an unreadable knob is RECORDED as a failure, not swallowed"
}

# The fixture leg: the harness driven against a synthetic debugfs built from the
# same table the driver source validates, with the driver's one-shot semantics
# simulated. This is what makes "the counter names are right" checkable on a
# workstation instead of costing a board session.
selftest_fixture() {
	local work="$1" knob

	QA_DEBUGFS="${work}/rkvenc-test"
	qa_fixture_make "${QA_DEBUGFS}" rkvenc

	for knob in fail_service_attach_once fail_ccu_attach_once \
			fail_irq_request_once fail_clock_enable_once \
			fail_session_alloc_once delay_task_completion_ms; do
		QA_FAILURES=0
		qa_arm "${knob}" 1 >/dev/null 2>&1
		qa_fixture_consume "${QA_DEBUGFS}" rkvenc "${knob}"
		qa_assert_consumed >/dev/null 2>&1
		check "$([[ ${QA_FAILURES} -eq 0 ]] && echo 1 || echo 0)" \
			"fixture: ${knob} arms, fires once and auto-resets"
	done

	# A driver that IGNORED the knob leaves the counter at 0 and the knob
	# armed. That must be a failure, or every case could pass vacuously.
	QA_FAILURES=0
	qa_arm fail_service_attach_once 1 >/dev/null 2>&1
	qa_assert_consumed >/dev/null 2>&1
	check "$([[ ${QA_FAILURES} -gt 0 ]] && echo 1 || echo 0)" \
		"fixture: an unconsumed knob is reported as a FAILURE"

	# ...and so must a counter that moved TWICE.
	QA_FAILURES=0
	printf '0\n' >"${QA_DEBUGFS}/fail_service_attach_once"
	qa_arm fail_service_attach_once 1 >/dev/null 2>&1
	qa_fixture_consume_twice "${QA_DEBUGFS}" rkvenc fail_service_attach_once
	qa_assert_consumed >/dev/null 2>&1
	check "$([[ ${QA_FAILURES} -gt 0 ]] && echo 1 || echo 0)" \
		"fixture: a counter that moved twice is reported as a FAILURE"

	# The old, wrong name must now be absent from the fixture AND rejected by
	# the table, so the previous spelling cannot come back unnoticed.
	check "$([[ ! -e "${QA_DEBUGFS}/fail_service_attach_consumed" ]] && echo 1 || echo 0)" \
		"fixture: the pre-fix name fail_service_attach_consumed does not exist"
}

run_self_test() {
	local work rc=0
	SELFTEST_RC=0
	work="$(mktemp -d)"

	selftest_regressions "${work}"
	selftest_fixture "${work}"
	rc="${SELFTEST_RC}"

	# qa_result must refuse to print PASS while a failure is recorded.
	QA_FAILURES=1
	if qa_result self-test >/dev/null 2>&1; then
		printf '  FAIL qa_result printed PASS with a recorded failure\n' >&2
		rc=1
	else
		printf '  ok  qa_result refuses PASS while a failure is recorded\n'
	fi

	QA_FAILURES=0
	if qa_result self-test | grep -q '^RESULT=PASS case=self-test$'; then
		printf '  ok  the RESULT= contract line is exact\n'
	else
		printf '  FAIL the RESULT= contract line drifted\n' >&2
		rc=1
	fi

	rm -rf "${work}"
	(( rc == 0 )) && printf 'RESULT=PASS case=self-test\n'
	return "${rc}"
}

# ---------------------------------------------------------------------------

main() {
	local self_test=0

	while (( $# )); do
		case "$1" in
			--case)      QA_CASE="${2:-}"; shift 2 ;;
			--case=*)    QA_CASE="${1#--case=}"; shift ;;
			--debugfs)   QA_DEBUGFS="${2:-}"; shift 2 ;;
			--debugfs=*) QA_DEBUGFS="${1#--debugfs=}"; shift ;;
			--device)    QA_DEVICE="${2:-}"; shift 2 ;;
			--device=*)  QA_DEVICE="${1#--device=}"; shift ;;
			--delay-ms)  QA_DELAY_MS="${2:-}"; shift 2 ;;
			--delay-ms=*) QA_DELAY_MS="${1#--delay-ms=}"; shift ;;
			--self-test) self_test=1; shift ;;
			-h|--help)   usage; return 0 ;;
			*) usage >&2; qa_die "unknown argument: $1" ;;
		esac
	done

	(( self_test )) && { run_self_test; return $?; }

	[[ -n "${QA_CASE}" ]] || { usage >&2; qa_die "--case is required"; }
	[[ -d "${QA_DEBUGFS}" ]] \
		|| qa_die "${QA_DEBUGFS} not present — is this an edge-test kernel with debugfs mounted?"
	qa_require_cmd gst-launch-1.0 dmesg timeout stat

	case "${QA_CASE}" in
		fail-service-attach)
			run_bind_fault_case fail-service-attach fail_service_attach_once ;;
		fail-ccu-attach)
			run_bind_fault_case fail-ccu-attach fail_ccu_attach_once ;;
		fail-irq-request)
			run_bind_fault_case fail-irq-request fail_irq_request_once ;;
		fail-clock-enable) run_fail_clock_enable ;;
		delayed-teardown)  run_delayed_teardown ;;
		*) qa_die "unknown case: ${QA_CASE}" ;;
	esac
}

main "$@"
