#!/usr/bin/env bash
#
# qa-common.sh — shared vocabulary for the on-board CeraLive kernel QA harnesses.
#
# These scripts run on a REAL Rock 5B+ booted into the non-shipping `edge-test`
# kernel, under KASAN and lockdep, and their transcripts are the evidence that
# the Wave-6 driver fixes actually work. Two consequences shape everything here:
#
#   1. THE OUTPUT IS A CONTRACT. A passing case prints exactly one line starting
#      `RESULT=PASS case=<name>` and exits 0; anything else exits non-zero. A
#      harness that "mostly worked" must fail, because its transcript is quoted
#      as proof.
#   2. NOTHING MAY PASS VACUOUSLY. Every fault case asserts the injected error
#      actually fired — the consumed counter incremented by exactly one and the
#      one-shot knob reset itself — before it looks at anything else. A driver
#      that silently ignored the knob would otherwise produce a clean run and a
#      green transcript.
#
# Profile: `set -uo pipefail` without `-e`. These harnesses run destructive-ish
# operations (driver unbind) and must reach their own cleanup and footer rather
# than abort half way through with a device detached.
#
# shellcheck shell=bash

QA_FAILURES=0

qa_log()  { printf '  %s\n' "$*"; }
qa_warn() { printf '  WARN %s\n' "$*" >&2; }

qa_fail() {
	QA_FAILURES=$(( QA_FAILURES + 1 ))
	printf '  FAIL %s\n' "$*" >&2
}

qa_die() {
	printf 'ERROR %s\n' "$*" >&2
	exit 2
}

qa_require_cmd() {
	local cmd
	for cmd in "$@"; do
		command -v "${cmd}" >/dev/null 2>&1 \
			|| qa_die "required command not found: ${cmd}"
	done
}

# qa_result <case> [extra key=value ...]
#
# The single exit point. Emits the contract line only when nothing failed, so a
# harness cannot report PASS and a failure in the same transcript.
qa_result() {
	local case_name="$1"; shift
	if (( QA_FAILURES != 0 )); then
		printf 'RESULT=FAIL case=%s failures=%d\n' "${case_name}" "${QA_FAILURES}" >&2
		return 1
	fi
	printf 'RESULT=PASS case=%s%s\n' "${case_name}" "${*:+ $*}"
	return 0
}

# ---------------------------------------------------------------------------
# debugfs knobs
# ---------------------------------------------------------------------------

qa_knob_path() { printf '%s/%s' "${QA_DEBUGFS}" "$1"; }

qa_read_knob() {
	local path
	path="$(qa_knob_path "$1")"
	[[ -r "${path}" ]] || { qa_fail "knob not readable: ${path}"; printf 'ERR'; return 1; }
	cat "${path}"
}

qa_write_knob() {
	local path
	path="$(qa_knob_path "$1")"
	[[ -w "${path}" ]] || { qa_fail "knob not writable: ${path}"; return 1; }
	printf '%s\n' "$2" >"${path}" || { qa_fail "write ${2} -> ${path} failed"; return 1; }
}

qa_assert_eq() {
	local want="$1" got="$2" what="$3"
	if [[ "${want}" == "${got}" ]]; then
		qa_log "ok ${what} = ${got}"
	else
		qa_fail "${what}: want '${want}', got '${got}'"
	fi
}

# qa_arm <knob> <value>
#
# Records the knob's consumed counter so qa_assert_consumed can prove the fault
# fired exactly once rather than zero or twice.
qa_arm() {
	local knob="$1" value="$2" counter="$3"
	QA_ARMED_KNOB="${knob}"
	QA_ARMED_COUNTER="${counter}"
	QA_ARMED_BEFORE="$(qa_read_knob "${counter}")"
	qa_write_knob "${knob}" "${value}" || return 1
	qa_assert_eq "${value}" "$(qa_read_knob "${knob}")" "armed ${knob}"
}

# qa_assert_consumed — the non-vacuity check every fault case runs FIRST.
qa_assert_consumed() {
	local after want
	after="$(qa_read_knob "${QA_ARMED_COUNTER}")"
	want=$(( QA_ARMED_BEFORE + 1 ))
	qa_assert_eq "${want}" "${after}" "${QA_ARMED_COUNTER} incremented exactly once"
	qa_assert_eq "0" "$(qa_read_knob "${QA_ARMED_KNOB}")" "${QA_ARMED_KNOB} auto-reset"
}

# ---------------------------------------------------------------------------
# Encode probe — "and the device still works afterwards"
# ---------------------------------------------------------------------------

QA_ENCODE_FRAMES="${QA_ENCODE_FRAMES:-60}"

# qa_encode <label> — a real hardware encode, asserted by OUTPUT SIZE.
#
# A zero-byte file with a zero exit status is the exact shape the truncated-DMA
# defect produced, so the byte count is the assertion and the exit status is
# only the first half of it.
qa_encode() {
	local label="$1" out rc size
	out="$(mktemp -t ceralive-qa-encode.XXXXXX.h264)"

	timeout 120 gst-launch-1.0 -q \
		videotestsrc num-buffers="${QA_ENCODE_FRAMES}" \
		! video/x-raw,format=NV12,width=1920,height=1080 \
		! mpph264enc ! h264parse ! filesink location="${out}" \
		>/dev/null 2>&1
	rc=$?
	size=$(stat -c %s "${out}" 2>/dev/null || printf 0)
	rm -f "${out}"

	if (( rc == 0 )) && (( size > 0 )); then
		qa_log "ok ${label}: ${QA_ENCODE_FRAMES}-frame encode produced ${size} bytes"
		return 0
	fi
	qa_fail "${label}: encode rc=${rc} bytes=${size}"
	return 1
}

# qa_encode_expect_failure <label> — the fault case's positive assertion.
qa_encode_expect_failure() {
	local label="$1" out rc
	out="$(mktemp -t ceralive-qa-encode.XXXXXX.h264)"

	timeout 120 gst-launch-1.0 -q \
		videotestsrc num-buffers="${QA_ENCODE_FRAMES}" \
		! video/x-raw,format=NV12,width=1920,height=1080 \
		! mpph264enc ! h264parse ! filesink location="${out}" \
		>/dev/null 2>&1
	rc=$?
	rm -f "${out}"

	if (( rc != 0 )); then
		qa_log "ok ${label}: encode failed as expected (rc=${rc})"
		return 0
	fi
	qa_fail "${label}: encode SUCCEEDED while a fault was armed"
	return 1
}

# ---------------------------------------------------------------------------
# Kernel-log screening
# ---------------------------------------------------------------------------

# qa_dmesg_since <marker-file> — dmesg lines emitted after the marker was taken.
qa_dmesg_mark() { dmesg | wc -l; }

qa_assert_no_sanitizer_report() {
	local since="$1" label="$2" hits
	hits="$(dmesg | tail -n +"$(( since + 1 ))" |
		grep -nE 'BUG:|Oops|KASAN: [a-z-]+ in |WARNING: possible circular locking dependency|possible recursive locking|INFO: task .* blocked|Kernel panic|Tainted:' || true)"
	if [[ -z "${hits}" ]]; then
		qa_log "ok ${label}: no sanitizer/lockdep report"
	else
		qa_fail "${label}: kernel reported:"
		printf '%s\n' "${hits}" >&2
	fi
}
