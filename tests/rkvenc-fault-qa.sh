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
# the assertion is on the write, captured through a subshell so a failing write
# cannot abort the harness before its cleanup.
qa_bind_expect_errno() {
	local dev="$1" want="$2" err rc
	err="$( { printf '%s' "${dev}" >"${QA_DRIVER_DIR}/bind"; } 2>&1 )"
	rc=$?
	if (( rc == 0 )); then
		qa_fail "bind of ${dev} SUCCEEDED while a fault was armed"
		return 1
	fi
	if grep -qi -- "${want}" <<<"${err}"; then
		qa_log "ok bind of ${dev} failed with ${want}"
		return 0
	fi
	qa_fail "bind of ${dev}: expected ${want}, got: ${err}"
	return 1
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
	local case_name="$1" knob="$2" counter="$3" errno="$4"
	local core mark

	core="$(qa_first_core)"
	mark="$(qa_dmesg_mark)"

	qa_unbind "${core}" || qa_fail "could not unbind ${core}"
	qa_arm "${knob}" 1 "${counter}" || return 1
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

	qa_arm fail_clock_enable_once 1 fail_clock_enable_consumed || return 1
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

	qa_arm delay_task_completion_ms "${QA_DELAY_MS}" delay_consumed || return 1

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

run_self_test() {
	local work rc=0
	work="$(mktemp -d)"

	QA_DEBUGFS="${work}/rkvenc-test"
	mkdir -p "${QA_DEBUGFS}"
	printf '0\n' >"${QA_DEBUGFS}/fail_service_attach_once"
	printf '0\n' >"${QA_DEBUGFS}/fail_service_attach_consumed"

	QA_FAILURES=0
	qa_arm fail_service_attach_once 1 fail_service_attach_consumed >/dev/null

	# A driver that IGNORED the knob leaves the counter at 0 and the knob
	# armed. That must be a failure, or every case could pass vacuously.
	qa_assert_consumed >/dev/null 2>&1
	if (( QA_FAILURES > 0 )); then
		printf '  ok  an unconsumed knob is reported as a FAILURE\n'
	else
		printf '  FAIL an unconsumed knob passed\n' >&2
		rc=1
	fi

	QA_FAILURES=0
	printf '1\n' >"${QA_DEBUGFS}/fail_service_attach_consumed"
	printf '0\n' >"${QA_DEBUGFS}/fail_service_attach_once"
	qa_assert_consumed >/dev/null 2>&1
	if (( QA_FAILURES == 0 )); then
		printf '  ok  a consumed, auto-reset knob passes\n'
	else
		printf '  FAIL a correctly consumed knob was rejected\n' >&2
		rc=1
	fi

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
			run_bind_fault_case fail-service-attach \
				fail_service_attach_once fail_service_attach_consumed ENOMEM ;;
		fail-ccu-attach)
			run_bind_fault_case fail-ccu-attach \
				fail_ccu_attach_once fail_ccu_attach_consumed ENODEV ;;
		fail-irq-request)
			run_bind_fault_case fail-irq-request \
				fail_irq_request_once fail_irq_request_consumed EBUSY ;;
		fail-clock-enable) run_fail_clock_enable ;;
		delayed-teardown)  run_delayed_teardown ;;
		*) qa_die "unknown case: ${QA_CASE}" ;;
	esac
}

main "$@"
