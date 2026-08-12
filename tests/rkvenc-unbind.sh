#!/usr/bin/env bash
#
# rkvenc-unbind.sh — prove the rkvenc teardown is safe while work is in flight.
#
# RUNS ON HARDWARE ONLY, on the non-shipping `edge-test` kernel (KASAN +
# lockdep). This is the harness for the teardown/unwind work: a supplier device
# (the MPP service, or the CCU) is unbound while consumers are live, and the
# driver has to quiesce them rather than free state somebody still holds.
#
# THE HARNESS CONTRACT, and it is load-bearing rather than convenience:
# the held-open-FD case DELIBERATELY holds a file descriptor across the unbind,
# observes that the driver has started refusing new work with -ENODEV, and only
# THEN closes it. The driver is required to wait for that close; a driver that
# freed the session while the FD was open would corrupt memory instead of
# blocking, and only KASAN would see it. So the harness must not close early,
# and it must not close late either -- a bounded timeout is what turns "waits
# for the reference" into a testable claim rather than a hang.
#
# The negative fixture is the other half. `--states timeout-negative` runs the
# same held-FD case and NEVER closes the descriptor: the unbind must then hit
# the timeout and the case must FAIL. A harness that cannot fail is not evidence,
# and a "waits for every reference" claim that is satisfied by a driver which
# simply does not wait is exactly the mistake this fixture exists to catch.
#
# Usage:
#   rkvenc-unbind.sh [--device /dev/mpp_service]
#                    [--states idle,held-open-fd,inflight]
#                    [--iterations 20] [--unbind-timeout 15]
#   rkvenc-unbind.sh --self-test        # host-side, no hardware, no root

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/qa-common.sh
source "${HERE}/lib/qa-common.sh"

# shellcheck disable=SC2034  # read by lib/qa-common.sh to pick this driver's control table
QA_DRIVER=rkvenc
QA_DEVICE="/dev/mpp_service"
QA_DEBUGFS="/sys/kernel/debug/rkvenc-test"
QA_STATES="idle,held-open-fd,inflight"
QA_ITERATIONS=20
QA_UNBIND_TIMEOUT=15
QA_DRIVER_DIR="${QA_DRIVER_DIR:-/sys/bus/platform/drivers/rkvenc}"
QA_DEVICE_DIR="${QA_DEVICE_DIR:-/sys/bus/platform/devices}"

usage() { sed -n '2,29p' "${BASH_SOURCE[0]}"; }

# ---------------------------------------------------------------------------
# Discovery. The driver binds three NODE KINDS -- the service, the CCU and the
# cores -- and which is a supplier of which is the whole subject of the test, so
# they are classified by node name rather than by a hardcoded address.
#
# They are enumerated from the BUS's device directory, never from the driver's
# own: a driver directory holds one symlink per BOUND device, and the device
# this harness must rebind is by definition NOT bound at that moment. Discovery
# there can only ever yield an empty name, so every bind write is skipped and
# the run mistakes "nothing asked it to probe" for "it refused to probe". No
# driver change can repair that -- the symlink's absence IS the driver core's
# record that the device is unbound.
#
# The driver directory keeps the job it is authoritative for: whether a device
# is currently BOUND (qa_is_bound), plus the bind/unbind attributes.
# ---------------------------------------------------------------------------

# A `case ... in ${var})` does NOT split alternations that arrive through a
# variable, so the patterns are split explicitly and matched one at a time.
qa_devices_matching() {
	local patterns="$1" entry name pattern
	for entry in "${QA_DEVICE_DIR}"/*; do
		[[ -e "${entry}" ]] || continue
		name="$(basename "${entry}")"
		local IFS='|'
		for pattern in ${patterns}; do
			unset IFS
			# shellcheck disable=SC2053  # deliberate glob match
			if [[ "${name}" == ${pattern} ]]; then
				printf '%s\n' "${name}"
				break
			fi
			local IFS='|'
		done
		unset IFS
	done
}

qa_service_device() { qa_devices_matching '*mpp-srv*|*mpp_service*|*mpp-service*' | head -1; }
qa_ccu_device()     { qa_devices_matching '*rkvenc-ccu*|*rkvenc_ccu*' | head -1; }
qa_core_devices()   { qa_devices_matching '*rkvenc-core*|*rkvenc_core*'; }

qa_is_bound() { [[ -n "${1:-}" && -e "${QA_DRIVER_DIR}/$1" ]]; }

# The states assert on a device that is present AND bound, which is what their
# "no service device bound" diagnostic has always claimed to mean.
qa_bound_service_device() {
	local svc; svc="$(qa_service_device)"
	qa_is_bound "${svc}" && printf '%s\n' "${svc}"
}

qa_unbind_bounded() {
	local dev="$1" start end
	start="$(date +%s)"
	timeout "${QA_UNBIND_TIMEOUT}" \
		sh -c "printf '%s' '${dev}' > '${QA_DRIVER_DIR}/unbind'" 2>/dev/null
	local rc=$?
	end="$(date +%s)"
	QA_UNBIND_SECONDS=$(( end - start ))
	return "${rc}"
}

qa_bind() {
	local dev="$1"
	timeout "${QA_UNBIND_TIMEOUT}" \
		sh -c "printf '%s' '${dev}' > '${QA_DRIVER_DIR}/bind'" 2>/dev/null
}

# Rebind order is part of the claim: a consumer may not come back before the
# supplier it depends on, or the device links did not do their job.
qa_rebind_all() {
	local svc ccu core
	svc="$(qa_service_device)"; ccu="$(qa_ccu_device)"
	qa_is_bound "${svc}" || { [[ -n "${svc}" ]] && qa_bind "${svc}"; }
	qa_is_bound "${ccu}" || { [[ -n "${ccu}" ]] && qa_bind "${ccu}"; }
	for core in $(qa_core_devices); do
		qa_is_bound "${core}" || qa_bind "${core}"
	done
	if [[ -e "${QA_DEVICE}" ]]; then
		qa_log "ok all devices rebound consumer-after-supplier (${QA_DEVICE} present)"
	else
		qa_fail "${QA_DEVICE} absent after rebind"
	fi
}

# ---------------------------------------------------------------------------
# The FD holder. A tiny background shell keeps the char device open with no
# ioctl in flight, so the ONLY thing keeping the session alive is the reference.
# ---------------------------------------------------------------------------

qa_hold_fd() {
	local fifo="$1"
	exec 9<>"${QA_DEVICE}" || return 1
	printf 'holding\n' >"${fifo}"
	read -r _ <"${fifo}"
	exec 9>&-
}

qa_open_must_fail_enodev() {
	local err
	err="$( { export LC_ALL=C; exec 8<>"${QA_DEVICE}"; } 2>&1 )"
	local rc=$?
	if (( rc == 0 )); then
		exec 8>&- || true
		qa_fail "open(${QA_DEVICE}) SUCCEEDED while unbind was pending"
		return 1
	fi
	# ENODEV's strerror string is a PREFIX of ENXIO's, so the old substring
	# match accepted "No such device or address" — a different failure — as a
	# pass. qa_errno_matches compares the phrase whole.
	if qa_errno_matches ENODEV "${err}"; then
		qa_log "ok new open during quiesce fails with ENODEV"
		return 0
	fi
	qa_fail "new open during quiesce: expected ENODEV, got $(qa_errno_from_text "${err}" || printf unrecognised): ${err}"
	return 1
}

# ---------------------------------------------------------------------------
# States
# ---------------------------------------------------------------------------

state_idle() {
	local svc mark
	svc="$(qa_bound_service_device)"
	[[ -n "${svc}" ]] || { qa_fail "no service device bound"; return 1; }
	mark="$(qa_dmesg_mark)"

	if qa_unbind_bounded "${svc}"; then
		qa_log "ok idle unbind of ${svc} completed in ${QA_UNBIND_SECONDS}s"
	else
		qa_fail "idle unbind of ${svc} did not complete within ${QA_UNBIND_TIMEOUT}s"
	fi
	qa_rebind_all
	qa_assert_no_sanitizer_report "${mark}" "unbind-idle"
	qa_encode "unbind-idle post-rebind"
}

state_held_open_fd() {
	local svc mark fifo expect_close="${1:-close}"
	svc="$(qa_bound_service_device)"
	[[ -n "${svc}" ]] || { qa_fail "no service device bound"; return 1; }
	mark="$(qa_dmesg_mark)"

	fifo="$(mktemp -u)"; mkfifo "${fifo}"
	qa_hold_fd "${fifo}" &
	local holder=$!
	read -r _ <"${fifo}"

	qa_unbind_bounded "${svc}" &
	local unbinder=$!

	# Give the driver a moment to enter its quiescing state, then prove it is
	# actually refusing new work rather than merely having been asked to stop.
	sleep 1
	qa_open_must_fail_enodev

	if [[ "${expect_close}" == "close" ]]; then
		printf 'release\n' >"${fifo}"
		wait "${holder}" 2>/dev/null
		if wait "${unbinder}"; then
			qa_log "ok held-FD unbind completed after the FD was closed"
		else
			qa_fail "held-FD unbind did not complete within ${QA_UNBIND_TIMEOUT}s after close"
		fi
		qa_rebind_all
		qa_assert_no_sanitizer_report "${mark}" "unbind-held-fd"
		qa_encode "unbind-held-fd post-rebind"
	else
		# The deliberate negative fixture: never close.
		if wait "${unbinder}"; then
			qa_fail "unbind COMPLETED with a file descriptor still open — the driver did not wait for the reference"
		else
			qa_log "ok negative fixture: unbind correctly did NOT complete while an FD was held"
		fi
		printf 'release\n' >"${fifo}"
		wait "${holder}" 2>/dev/null
		qa_rebind_all
		qa_assert_no_sanitizer_report "${mark}" "unbind-timeout-negative"
	fi
	rm -f "${fifo}"
}

state_inflight() {
	local svc mark i
	svc="$(qa_bound_service_device)"
	[[ -n "${svc}" ]] || { qa_fail "no service device bound"; return 1; }
	mark="$(qa_dmesg_mark)"

	# Queue real work, then unbind underneath it. The encode is EXPECTED to
	# fail; what must not happen is a sanitizer report, a hung waiter or an
	# unbind that never returns.
	( QA_ENCODE_FRAMES=600 qa_encode "inflight background" >/dev/null 2>&1 ) &
	local worker=$!
	sleep 2

	if qa_unbind_bounded "${svc}"; then
		qa_log "ok in-flight unbind completed in ${QA_UNBIND_SECONDS}s"
	else
		qa_fail "in-flight unbind did not complete within ${QA_UNBIND_TIMEOUT}s"
	fi

	if timeout 30 tail --pid="${worker}" -f /dev/null; then
		qa_log "ok the in-flight waiter woke rather than hanging"
	else
		qa_fail "the in-flight waiter never woke — a waiter was not woken with -ENODEV"
		kill -9 "${worker}" 2>/dev/null
	fi

	qa_rebind_all
	qa_assert_no_sanitizer_report "${mark}" "unbind-inflight"
	qa_encode "unbind-inflight post-rebind"

	for (( i = 1; i < QA_ITERATIONS; i++ )); do
		qa_unbind_bounded "${svc}" || qa_fail "repeat unbind ${i} timed out"
		qa_rebind_all >/dev/null
	done
	qa_log "ok ${QA_ITERATIONS} unbind/rebind cycles completed"
	qa_encode "unbind-inflight after ${QA_ITERATIONS} cycles"
}

# ---------------------------------------------------------------------------

run_self_test() {
	local rc=0 work
	work="$(mktemp -d)"

	# Device classification must be driven by node NAME, never by an address,
	# or a DT change silently selects nothing and the harness passes vacuously.
	QA_DRIVER_DIR="${work}/drivers/rkvenc"
	QA_DEVICE_DIR="${work}/devices"
	mkdir -p "${QA_DRIVER_DIR}" "${QA_DEVICE_DIR}"
	for node in fdba0000.mpp-srv fdbd0000.rkvenc-ccu fdbd0000.rkvenc-core fdbe0000.rkvenc-core; do
		mkdir -p "${QA_DEVICE_DIR}/${node}"
		ln -s "../../devices/${node}" "${QA_DRIVER_DIR}/${node}"
	done

	if [[ "$(qa_service_device)" == "fdba0000.mpp-srv" ]]; then
		printf '  ok  the service device is discovered by node name\n'
	else
		printf '  FAIL service discovery: got "%s"\n' "$(qa_service_device)" >&2; rc=1
	fi
	if [[ "$(qa_ccu_device)" == "fdbd0000.rkvenc-ccu" ]]; then
		printf '  ok  the CCU device is discovered by node name\n'
	else
		printf '  FAIL ccu discovery: got "%s"\n' "$(qa_ccu_device)" >&2; rc=1
	fi
	if [[ "$(qa_core_devices | wc -l)" -eq 2 ]]; then
		printf '  ok  both cores are discovered, and the CCU is not counted as one\n'
	else
		printf '  FAIL core discovery: got %s\n' "$(qa_core_devices | wc -l)" >&2; rc=1
	fi

	# The regression that made every unbind case unreachable: an UNBOUND
	# device is gone from the driver directory but still on the bus, and it is
	# the one the harness has to find in order to bind it back.
	rm -f "${QA_DRIVER_DIR}/fdba0000.mpp-srv"
	if [[ "$(qa_service_device)" == "fdba0000.mpp-srv" ]]; then
		printf '  ok  an UNBOUND service device is still discovered (so it can be rebound)\n'
	else
		printf '  FAIL an unbound service device was not discovered: got "%s"\n' \
			"$(qa_service_device)" >&2; rc=1
	fi
	if qa_is_bound fdba0000.mpp-srv; then
		printf '  FAIL an unbound service device was reported as bound\n' >&2; rc=1
	else
		printf '  ok  an unbound service device is reported as NOT bound\n'
	fi
	if [[ -z "$(qa_bound_service_device)" ]]; then
		printf '  ok  the states refuse to run against an unbound service device\n'
	else
		printf '  FAIL an unbound service device satisfied a state precondition\n' >&2; rc=1
	fi
	ln -s "../../devices/fdba0000.mpp-srv" "${QA_DRIVER_DIR}/fdba0000.mpp-srv"
	if [[ "$(qa_bound_service_device)" == "fdba0000.mpp-srv" ]]; then
		printf '  ok  a rebound service device satisfies the state precondition again\n'
	else
		printf '  FAIL a rebound service device was not accepted\n' >&2; rc=1
	fi

	# A missing device directory must be loud, never an empty (vacuous) run.
	QA_DEVICE_DIR="${work}/absent"
	if [[ -z "$(qa_service_device)" ]]; then
		printf '  ok  an absent device directory yields no device (caller must fail)\n'
	else
		printf '  FAIL an absent device directory yielded a device\n' >&2; rc=1
	fi
	QA_DEVICE_DIR="${work}/devices"

	# The quiesce assertion reads an errno out of a shell diagnostic, and the
	# two errnos it has to tell apart differ only by a trailing "or address".
	if qa_errno_matches ENODEV 'bash: /dev/mpp_service: No such device'; then
		printf '  ok  the real ENODEV diagnostic is recognised\n'
	else
		printf '  FAIL the real ENODEV diagnostic was not recognised\n' >&2; rc=1
	fi
	if qa_errno_matches ENODEV 'bash: /dev/mpp_service: No such device or address'; then
		printf '  FAIL ENXIO was accepted as ENODEV\n' >&2; rc=1
	else
		printf '  ok  ENXIO is not accepted as ENODEV\n'
	fi

	# The negative fixture must be reachable by name, or nobody will run it.
	if grep -q 'timeout-negative' "${BASH_SOURCE[0]}"; then
		printf '  ok  the timeout-negative fixture is selectable\n'
	else
		printf '  FAIL the timeout-negative fixture is not selectable\n' >&2; rc=1
	fi

	rm -rf "${work}"
	(( rc == 0 )) && printf 'RESULT=PASS case=self-test\n'
	return "${rc}"
}

main() {
	local self_test=0 state

	while (( $# )); do
		case "$1" in
			--device)          QA_DEVICE="${2:-}"; shift 2 ;;
			--device=*)        QA_DEVICE="${1#--device=}"; shift ;;
			--debugfs)         QA_DEBUGFS="${2:-}"; shift 2 ;;
			--debugfs=*)       QA_DEBUGFS="${1#--debugfs=}"; shift ;;
			--states)          QA_STATES="${2:-}"; shift 2 ;;
			--states=*)        QA_STATES="${1#--states=}"; shift ;;
			--iterations)      QA_ITERATIONS="${2:-}"; shift 2 ;;
			--iterations=*)    QA_ITERATIONS="${1#--iterations=}"; shift ;;
			--unbind-timeout)  QA_UNBIND_TIMEOUT="${2:-}"; shift 2 ;;
			--unbind-timeout=*) QA_UNBIND_TIMEOUT="${1#--unbind-timeout=}"; shift ;;
			--self-test)       self_test=1; shift ;;
			-h|--help)         usage; return 0 ;;
			*) usage >&2; qa_die "unknown argument: $1" ;;
		esac
	done

	(( self_test )) && { run_self_test; return $?; }

	[[ -d "${QA_DRIVER_DIR}" ]] || qa_die "driver directory absent: ${QA_DRIVER_DIR}"
	[[ -d "${QA_DEBUGFS}" ]] \
		|| qa_warn "${QA_DEBUGFS} absent — unbind cases run, but no fault can be armed"
	qa_require_cmd gst-launch-1.0 dmesg timeout stat mkfifo

	local IFS=','
	for state in ${QA_STATES}; do
		unset IFS
		printf '== state: %s\n' "${state}"
		case "${state}" in
			idle)             state_idle ;;
			held-open-fd)     state_held_open_fd close ;;
			inflight)         state_inflight ;;
			timeout-negative) state_held_open_fd no-close ;;
			*) qa_die "unknown state: ${state}" ;;
		esac
		local IFS=','
	done
	unset IFS

	qa_result "rkvenc-unbind" "states=${QA_STATES}" "iterations=${QA_ITERATIONS}"
}

main "$@"
