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

QA_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The syscall-level errno helper is optional: it is built beside the ioctl
# harness and copied to the board with it, and everything still works without it
# on the shell's own diagnostics.
QA_WRITE_ERRNO_BIN="${QA_WRITE_ERRNO_BIN:-}"
if [[ -z "${QA_WRITE_ERRNO_BIN}" ]]; then
	for _qa_cand in "${QA_LIB_DIR}/../qa-write-errno" \
			"${QA_LIB_DIR}/qa-write-errno" \
			"$(command -v qa-write-errno 2>/dev/null || true)"; do
		if [[ -n "${_qa_cand}" && -x "${_qa_cand}" ]]; then
			QA_WRITE_ERRNO_BIN="${_qa_cand}"
			break
		fi
	done
	unset _qa_cand
fi

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
# The fault-control table — DRIVER TRUTH, not a naming convention
#
# The two test drivers name their consumed counters DIFFERENTLY, and a harness
# that templates one pattern over both is wrong on the board and green on the
# workstation. rkvenc registers each knob through a helper that appends
# `_consumed` to the FULL knob name, so a knob that already ends in `_once`
# yields `<knob>_once_consumed`; the HDMI-RX driver registers its two counters
# by hand, without the `_once`. That is a fact about
# patches/0013 and patches/0017, so it is written down as data here and the
# callers never spell a counter name at all — see qa_arm().
#
# Verified against the driver sources on 2026-08-10 (see
# qa_verify_controls_against_patches, which re-derives this from the patches
# themselves so the table cannot silently drift from the kernel it tests).
# ---------------------------------------------------------------------------

declare -gA QA_FAULT_COUNTER=(
	[rkvenc:delay_task_completion_ms]=delay_consumed
	[rkvenc:fail_service_attach_once]=fail_service_attach_once_consumed
	[rkvenc:fail_ccu_attach_once]=fail_ccu_attach_once_consumed
	[rkvenc:fail_irq_request_once]=fail_irq_request_once_consumed
	[rkvenc:fail_clock_enable_once]=fail_clock_enable_once_consumed
	[rkvenc:fail_session_alloc_once]=fail_session_alloc_once_consumed
	[hdmirx:delay_worker_ms]=delay_worker_consumed
	[hdmirx:fail_clk_set_rate_once]=fail_clk_set_rate_consumed
)

# The errno each rkvenc fault knob makes its path return, so a case cannot
# assert one errno while arming a knob that produces another.
declare -gA QA_FAULT_ERRNO=(
	[rkvenc:fail_service_attach_once]=ENOMEM
	[rkvenc:fail_ccu_attach_once]=ENODEV
	[rkvenc:fail_irq_request_once]=EBUSY
	[rkvenc:fail_clock_enable_once]=EIO
	[rkvenc:fail_session_alloc_once]=ENOMEM
	[hdmirx:fail_clk_set_rate_once]=EIO
)

# Which driver's table the current harness is asking about.
QA_DRIVER="${QA_DRIVER:-rkvenc}"

# qa_counter_for <knob> — the counter node that pairs with <knob>, or a hard
# stop. An unknown knob is a harness bug, never a device condition, so it dies
# rather than accumulating a failure.
qa_counter_for() {
	local knob="$1" key="${QA_DRIVER}:$1"
	[[ -n "${QA_FAULT_COUNTER[${key}]:-}" ]] \
		|| qa_die "no counter registered for ${QA_DRIVER} knob '${knob}' — add it to QA_FAULT_COUNTER in lib/qa-common.sh"
	printf '%s' "${QA_FAULT_COUNTER[${key}]}"
}

# qa_errno_for <knob> — the errno the knob's path must return, or empty for the
# value knobs, which fail nothing.
qa_errno_for() { printf '%s' "${QA_FAULT_ERRNO[${QA_DRIVER}:$1]:-}"; }

# qa_controls_for <driver> — every node (knobs AND counters) that driver
# creates, one per line. The fixture builds itself from this, so a fixture can
# never contain a node the driver does not.
qa_controls_for() {
	local driver="$1" key
	for key in "${!QA_FAULT_COUNTER[@]}"; do
		[[ "${key}" == "${driver}:"* ]] || continue
		printf '%s\n%s\n' "${key#*:}" "${QA_FAULT_COUNTER[${key}]}"
	done | sort
}

# qa_verify_controls_against_patches <repo-root>
#
# Re-derives the node names from the DRIVER SOURCE in patches/ and compares them
# with the table above. This is the check that would have caught the wrong
# counter names on the workstation instead of on the board; it runs wherever the
# patches are present (the repo) and is skipped where they are not (a board,
# which only ever receives tests/).
#
# Returns 0 on agreement, 1 on drift, 77 when the sources are not present.
qa_verify_controls_against_patches() {
	local root="$1" rkvenc="" hdmirx="" p
	for p in "${root}"/patches/*rkvenc-ceralive-test-instrumentation.patch; do
		[[ -r "${p}" ]] && rkvenc="${p}"
	done
	for p in "${root}"/patches/*hdmirx-audio-lifecycle-and-clock-errors.patch; do
		[[ -r "${p}" ]] && hdmirx="${p}"
	done
	[[ -n "${rkvenc}" && -n "${hdmirx}" ]] || return 77

	local rc=0 driver src want got

	for driver in rkvenc hdmirx; do
		[[ "${driver}" == rkvenc ]] && src="${rkvenc}" || src="${hdmirx}"

		# Every node the driver actually creates. The rkvenc helper builds
		# `<name>_consumed` with snprintf, so the literal argument names
		# alone are not the whole set — the helper's callers contribute a
		# counter each, which is exactly the naming rule that was misread.
		got="$( {
			sed -n 's/.*debugfs_create_atomic_t("\([a-z0-9_]*\)".*/\1/p' "${src}"
			sed -n 's/.*rkvenc_test_add_knob("\([a-z0-9_]*\)".*/\1\n\1_consumed/p' "${src}"
		} | sort -u )"

		want="$(qa_controls_for "${driver}")"
		if [[ "${want}" != "${got}" ]]; then
			qa_fail "${driver}: the fault-control table disagrees with the driver source"
			diff <(printf '%s\n' "${want}") <(printf '%s\n' "${got}") \
				--label 'qa-common.sh table' --label "${src##*/}" -u >&2
			rc=1
		fi
	done
	return "${rc}"
}

# ---------------------------------------------------------------------------
# errno vocabulary
#
# A failed write reaches the harness as TEXT, and the text is the C library's
# strerror string ("Cannot allocate memory"), never the symbol the driver
# returned (`-ENOMEM`). Matching the symbol against that text can never succeed,
# for any case, however correct the driver is — so the mapping is explicit, and
# every errno the harness can plausibly meet is in it rather than just the one
# that was observed failing.
#
# The strings are the glibc/musl C-locale ones, which is why every capture in
# this file forces LC_ALL=C: a localised board would otherwise print a phrase
# that matches nothing.
# ---------------------------------------------------------------------------

declare -gA QA_ERRNO_STRERROR=(
	[EPERM]="Operation not permitted"
	[ENOENT]="No such file or directory"
	[ESRCH]="No such process"
	[EINTR]="Interrupted system call"
	[EIO]="Input/output error"
	[ENXIO]="No such device or address"
	[E2BIG]="Argument list too long"
	[EBADF]="Bad file descriptor"
	[EAGAIN]="Resource temporarily unavailable"
	[ENOMEM]="Cannot allocate memory"
	[EACCES]="Permission denied"
	[EFAULT]="Bad address"
	[EBUSY]="Device or resource busy"
	[EEXIST]="File exists"
	[ENODEV]="No such device"
	[ENOTDIR]="Not a directory"
	[EISDIR]="Is a directory"
	[EINVAL]="Invalid argument"
	[ENFILE]="Too many open files in system"
	[EMFILE]="Too many open files"
	[ENOTTY]="Inappropriate ioctl for device"
	[ENOSPC]="No space left on device"
	[EROFS]="Read-only file system"
	[EPIPE]="Broken pipe"
	[ERANGE]="Numerical result out of range"
	[ENOSYS]="Function not implemented"
	[EOPNOTSUPP]="Operation not supported"
	[ETIMEDOUT]="Connection timed out"
	# Kernel-internal, never translated by libc: a probe that defers shows up
	# as the raw number, and reading it as "some other failure" would be wrong.
	[EPROBE_DEFER]="Unknown error 517"
)

declare -gA QA_ERRNO_NUMBER=(
	[EPERM]=1   [ENOENT]=2  [ESRCH]=3   [EINTR]=4   [EIO]=5     [ENXIO]=6
	[E2BIG]=7   [EBADF]=9   [EAGAIN]=11 [ENOMEM]=12 [EACCES]=13 [EFAULT]=14
	[EBUSY]=16  [EEXIST]=17 [ENODEV]=19 [ENOTDIR]=20 [EISDIR]=21 [EINVAL]=22
	[ENFILE]=23 [EMFILE]=24 [ENOTTY]=25 [ENOSPC]=28 [EROFS]=30  [EPIPE]=32
	[ERANGE]=34 [ENOSYS]=38 [EOPNOTSUPP]=95 [ETIMEDOUT]=110 [EPROBE_DEFER]=517
)

# qa_errno_phrase <text> — the strerror phrase carried by a shell error message.
#
# Diagnostics arrive as `<who>: <what>: <strerror>` with a varying number of
# leading `<who>:` fields ("printf: write error: …", "bash: line 1: printf:
# write error: …", "sh: /sys/…: …"). The phrase is what follows the LAST ": ",
# which is stable across all of them, and taking it exactly is what keeps
# "No such device" from matching "No such device or address".
qa_errno_phrase() {
	local text="$1" line
	line="$(printf '%s' "${text}" | sed -e '/^[[:space:]]*$/d' | tail -1)"
	line="${line##*: }"
	line="${line#"${line%%[![:space:]]*}"}"
	line="${line%"${line##*[![:space:]]}"}"
	printf '%s' "${line}"
}

# qa_errno_from_text <text> — the errno SYMBOL a message reports, or the empty
# string. Used for the diagnostic half of a failed match: "expected ENOMEM, got
# EIO" is a report; "expected ENOMEM, got <a sentence>" is a puzzle.
qa_errno_from_text() {
	local text="$1" phrase sym
	phrase="$(qa_errno_phrase "${text}")"
	for sym in "${!QA_ERRNO_STRERROR[@]}"; do
		[[ "${phrase}" == "${QA_ERRNO_STRERROR[${sym}]}" ]] && { printf '%s' "${sym}"; return 0; }
	done
	# A bare symbol (some tools print it) or a raw `-19`-style report.
	for sym in "${!QA_ERRNO_STRERROR[@]}"; do
		[[ "${text}" =~ (^|[^A-Z_])${sym}([^A-Z_]|$) ]] && { printf '%s' "${sym}"; return 0; }
	done
	return 1
}

# qa_errno_matches <want-symbol> <text> [numeric-errno]
#
# True when the message reports <want-symbol>, whether it arrived as the symbol,
# as the C-locale strerror string, or as a raw errno number from the syscall
# helper. The numeric form is authoritative when present, because it is the
# value the kernel returned rather than a rendering of it.
qa_errno_matches() {
	local want="$1" text="$2" number="${3:-}"
	[[ -n "${QA_ERRNO_STRERROR[${want}]:-}" ]] \
		|| qa_die "unknown errno symbol in an assertion: ${want}"

	if [[ -n "${number}" && "${number}" =~ ^[0-9]+$ ]]; then
		[[ "${number}" == "${QA_ERRNO_NUMBER[${want}]}" ]]
		return $?
	fi
	[[ "$(qa_errno_phrase "${text}")" == "${QA_ERRNO_STRERROR[${want}]}" ]] && return 0
	[[ "${text}" =~ (^|[^A-Z_])${want}([^A-Z_]|$) ]] && return 0
	return 1
}

# qa_write_expect_errno <path> <data> <want-symbol> <label>
#
# Perform a write that MUST fail, and assert the errno.
#
# The syscall-level capture is preferred and is what QA_WRITE_ERRNO_BIN provides
# (tests/qa-write-errno.c, built beside the ioctl harness): it reports the raw
# errno number from write(2), so the assertion never depends on how some shell
# phrased the failure. Without it the shell's own message is parsed, under
# LC_ALL=C so the phrasing is at least deterministic.
qa_write_expect_errno() {
	local path="$1" data="$2" want="$3" label="$4"
	local err rc number="" got

	if [[ -n "${QA_WRITE_ERRNO_BIN:-}" && -x "${QA_WRITE_ERRNO_BIN}" ]]; then
		err="$("${QA_WRITE_ERRNO_BIN}" "${path}" "${data}" 2>&1)"
		rc=$?
		# The helper prints the bare errno number on failure.
		[[ "${err}" =~ ^[0-9]+$ ]] && number="${err}"
	else
		err="$( { LC_ALL=C printf '%s' "${data}" >"${path}"; } 2>&1 )"
		rc=$?
	fi

	if (( rc == 0 )); then
		qa_fail "${label}: the write SUCCEEDED where ${want} was required"
		return 1
	fi
	if qa_errno_matches "${want}" "${err}" "${number}"; then
		qa_log "ok ${label}: failed with ${want}${number:+ (errno ${number})}"
		return 0
	fi
	got="$(qa_errno_from_text "${err}" || true)"
	qa_fail "${label}: expected ${want}, got ${got:-unrecognised}: ${err}"
	return 1
}

# ---------------------------------------------------------------------------
# debugfs knobs
# ---------------------------------------------------------------------------

# A knob read that failed. It is NUMERIC on purpose: the previous sentinel was
# the literal string `ERR`, which `$(( ERR + 1 ))` in qa_assert_consumed then
# evaluated as a variable NAME, and under `set -u` an unset name aborts the
# whole harness mid-case — with the driver left unbound and no cleanup run. A
# sentinel must survive arithmetic, so it is a value no counter can hold.
QA_KNOB_READ_ERROR=-1

# Set before first use so `set -u` cannot fire on a case that asserts before it
# arms, and so an unarmed assertion is a reported FAILURE rather than an abort.
QA_ARMED_KNOB=""
QA_ARMED_COUNTER=""
QA_ARMED_BEFORE="${QA_KNOB_READ_ERROR}"

qa_knob_path() { printf '%s/%s' "${QA_DEBUGFS}" "$1"; }

qa_is_uint() { [[ "$1" =~ ^[0-9]+$ ]]; }

qa_read_knob() {
	local path value
	path="$(qa_knob_path "$1")"
	if [[ ! -r "${path}" ]]; then
		qa_fail "knob not readable: ${path}"
		printf '%s' "${QA_KNOB_READ_ERROR}"
		return 1
	fi
	value="$(cat "${path}" 2>/dev/null)" || {
		qa_fail "knob read failed: ${path}"
		printf '%s' "${QA_KNOB_READ_ERROR}"
		return 1
	}
	value="${value//[$' \t\r\n']/}"
	if ! qa_is_uint "${value}"; then
		qa_fail "knob ${path} did not read as a number: '${value}'"
		printf '%s' "${QA_KNOB_READ_ERROR}"
		return 1
	fi
	printf '%s' "${value}"
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
# fired exactly once rather than zero or twice. The counter is RESOLVED from the
# table rather than passed in: a caller that spells it is a caller that can
# misspell it, and a misspelt counter reads as "knob not readable", which is
# indistinguishable from a driver that never created it.
qa_arm() {
	local knob="$1" value="$2" counter before
	counter="$(qa_counter_for "${knob}")"

	QA_ARMED_KNOB="${knob}"
	QA_ARMED_COUNTER="${counter}"
	QA_ARMED_BEFORE="${QA_KNOB_READ_ERROR}"

	before="$(qa_read_knob "${counter}")" || {
		qa_fail "cannot arm ${knob}: its counter ${counter} is unreadable"
		return 1
	}
	QA_ARMED_BEFORE="${before}"

	qa_write_knob "${knob}" "${value}" || return 1
	qa_assert_eq "${value}" "$(qa_read_knob "${knob}")" "armed ${knob}"
}

# qa_assert_consumed — the non-vacuity check every fault case runs FIRST.
qa_assert_consumed() {
	local after want
	if [[ -z "${QA_ARMED_KNOB}" ]]; then
		qa_fail "qa_assert_consumed called with nothing armed"
		return 1
	fi
	if ! qa_is_uint "${QA_ARMED_BEFORE}"; then
		qa_fail "${QA_ARMED_COUNTER}: its pre-arm value was never read, so 'incremented exactly once' cannot be asserted"
		return 1
	fi

	# The read runs in a subshell, so its own qa_fail cannot reach this
	# shell's counter — the failure has to be recorded here or a case whose
	# counter vanished would report PASS.
	after="$(qa_read_knob "${QA_ARMED_COUNTER}")" || {
		qa_fail "${QA_ARMED_COUNTER}: unreadable after the fault, so consumption cannot be proven"
		return 1
	}
	want=$(( QA_ARMED_BEFORE + 1 ))
	qa_assert_eq "${want}" "${after}" "${QA_ARMED_COUNTER} incremented exactly once"
	qa_assert_eq "0" "$(qa_read_knob "${QA_ARMED_KNOB}")" "${QA_ARMED_KNOB} auto-reset"
}

# ---------------------------------------------------------------------------
# Kernel-log screening
#
# Defined before the encode probe because the probe asserts on the log: a
# fault-armed encode's verdict is what the DRIVER said, not what gst-launch-1.0
# returned.
# ---------------------------------------------------------------------------

# The command the screening reads the kernel ring buffer through. It is an array
# and not a string so the self-test can point it at a captured log fixture the
# same way the fixture legs point QA_DEBUGFS at a synthetic controls directory —
# which is what makes the assertions below checkable on a workstation instead of
# costing a board session. On a board it is `dmesg` and nothing else.
declare -ga QA_DMESG_CMD=(dmesg)

# qa_dmesg_mark — a line-count marker for qa_dmesg_since.
qa_dmesg_mark() { "${QA_DMESG_CMD[@]}" | wc -l; }

# qa_dmesg_since <marker> — the kernel-log lines emitted after the marker was
# taken.
qa_dmesg_since() { "${QA_DMESG_CMD[@]}" | tail -n +"$(( $1 + 1 ))"; }

qa_assert_no_sanitizer_report() {
	local since="$1" label="$2" hits
	hits="$(qa_dmesg_since "${since}" |
		grep -nE 'BUG:|Oops|KASAN: [a-z-]+ in |WARNING: possible circular locking dependency|possible recursive locking|INFO: task .* blocked|Kernel panic|Tainted:' || true)"
	if [[ -z "${hits}" ]]; then
		qa_log "ok ${label}: no sanitizer/lockdep report"
	else
		qa_fail "${label}: kernel reported:"
		printf '%s\n' "${hits}" >&2
	fi
}

# qa_assert_dmesg_count <marker> <extended-regex> <want-count> <what>
#
# The positive counterpart of qa_assert_no_sanitizer_report: some lines MUST be
# there, and the COUNT is the assertion. "at least one" is deliberately not
# accepted — a fault reported twice is a retry this series exists to rule out,
# and a fault reported zero times is a knob that was consumed without the task
# path noticing. Same reason qa_assert_consumed says "exactly once".
qa_assert_dmesg_count() {
	local since="$1" pattern="$2" want="$3" what="$4" got
	got="$(qa_dmesg_since "${since}" | grep -cE "${pattern}" || true)"
	qa_assert_eq "${want}" "${got}" "${what}"
}

# ---------------------------------------------------------------------------
# Encode probe — "and the device still works afterwards"
# ---------------------------------------------------------------------------

QA_ENCODE_FRAMES="${QA_ENCODE_FRAMES:-60}"

# The byte count a CLEAN QA_ENCODE_CANONICAL_FRAMES-frame run of the probe
# pipeline below produces. It is a MEASURED board constant, not a nominal one:
# every clean run of this exact pipeline across the 2026-08 campaign produced
# exactly 1,854,524 bytes, on a Rock 5B+ and on an Orange Pi 5 Plus, on debug and
# production kernels alike (docs/BOARD-QUALIFICATION.md §3e and §11).
#
# It exists so that "the fault-armed stream is measurably SHORTER" is an
# assertion rather than a story. The frame count is carried WITH it because the
# number means nothing without one, and both are overridable for a board that
# legitimately encodes to a different size — changing the constant is a visible
# diff, silently comparing against the wrong frame count would not be.
QA_ENCODE_CANONICAL_FRAMES="${QA_ENCODE_CANONICAL_FRAMES:-60}"
QA_ENCODE_CANONICAL_BYTES="${QA_ENCODE_CANONICAL_BYTES:-1854524}"

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

# qa_assert_fault_stream_shorter <label> <size>
#
# The stream half of a fault case's verdict, split out so it can be exercised
# with a byte count instead of a board.
#
# SHORTER says the frame really was lost. NON-EMPTY says this was an encode that
# lost a frame rather than a pipeline that never started — which is the shape the
# truncated-DMA defect produced and must not be mistaken for a successful fault
# injection. There is deliberately no tighter lower bound: the measured shortfall
# was 8.5 % for a single lost frame in sixty, far more than that frame's average
# share, because the loss perturbs the frames that reference it. Pinning "exactly
# one frame" is the kernel log's job, not arithmetic's.
qa_assert_fault_stream_shorter() {
	local label="$1" size="$2" short pct

	if (( size == 0 )); then
		qa_fail "${label}: the encode produced NO bytes — a dead pipeline, not a lost frame"
		return 1
	fi
	if (( size >= QA_ENCODE_CANONICAL_BYTES )); then
		qa_fail "${label}: ${size} bytes is not shorter than the canonical ${QA_ENCODE_CANONICAL_BYTES} — the lost frame was silently substituted"
		return 1
	fi

	# Tenths of a percent, rounded rather than truncated, so the number in a
	# transcript matches the 8.5 % recorded in BOARD-QUALIFICATION.md §11
	# instead of reading as 8.4 % and looking like a disagreement.
	short=$(( QA_ENCODE_CANONICAL_BYTES - size ))
	local tenths=$(( (short * 2000 + QA_ENCODE_CANONICAL_BYTES) / (QA_ENCODE_CANONICAL_BYTES * 2) ))
	printf -v pct '%d.%d' $(( tenths / 10 )) $(( tenths % 10 ))
	qa_log "ok ${label}: stream is ${size} bytes, ${short} short of the canonical ${QA_ENCODE_CANONICAL_BYTES} (${pct} %)"
	return 0
}

# qa_encode_expect_failure <label> — the fault case's positive assertion.
#
# WHAT IT DELIBERATELY DOES NOT GATE ON: gst-launch-1.0's exit status. That used
# to be the whole assertion and it is flaky BY CONSTRUCTION. The driver's
# -ENODEV is raced inside the closed-source librockchip-mpp, which turns it into
# `rc=0` with a short stream or `rc=134` (SIGABRT) with a truncated one depending
# only on how long the ioctl path took — two faces of one userspace race, neither
# of them a statement about the kernel. Measured in full in
# docs/BOARD-QUALIFICATION.md §11. The status is still LOGGED, because which face
# a run drew is worth having in the transcript.
#
# What it gates on instead is kernel-side and stream-side, and every part of it
# is STRICTER than the exit code it replaces:
#
#   1. the worker reported the fault exactly once (`hw_run failed: -<errno>`);
#   2. the POLL waiter was told the task aborted exactly once
#      (`wait result ret -19`, rkvenc_wait_result()'s -ENODEV arm); and
#   3. the stream is measurably shorter than a clean one, and not empty.
qa_encode_expect_failure() {
	local label="$1" out rc size mark errno errnum before="${QA_FAILURES}"

	# The errno is resolved from the ARMED knob rather than passed in, for
	# the same reason qa_arm resolves its own counter: a caller that spells
	# it is a caller that can misspell it, and a wrong errno here reads
	# exactly like a driver that never logged the failure at all.
	if [[ -z "${QA_ARMED_KNOB}" ]]; then
		qa_fail "${label}: called with nothing armed, so there is no fault to expect"
		return 1
	fi
	errno="$(qa_errno_for "${QA_ARMED_KNOB}")"
	if [[ -z "${errno}" ]]; then
		qa_fail "${label}: ${QA_ARMED_KNOB} injects no errno, so a failed encode cannot be asserted"
		return 1
	fi
	errnum="${QA_ERRNO_NUMBER[${errno}]}"

	if (( QA_ENCODE_FRAMES != QA_ENCODE_CANONICAL_FRAMES )); then
		qa_fail "${label}: the canonical ${QA_ENCODE_CANONICAL_BYTES}-byte reference was measured at ${QA_ENCODE_CANONICAL_FRAMES} frames, not ${QA_ENCODE_FRAMES} — set QA_ENCODE_CANONICAL_BYTES for this frame count"
		return 1
	fi

	out="$(mktemp -t ceralive-qa-encode.XXXXXX.h264)"
	mark="$(qa_dmesg_mark)"

	timeout 120 gst-launch-1.0 -q \
		videotestsrc num-buffers="${QA_ENCODE_FRAMES}" \
		! video/x-raw,format=NV12,width=1920,height=1080 \
		! mpph264enc ! h264parse ! filesink location="${out}" \
		>/dev/null 2>&1
	rc=$?
	# MEASURED BEFORE IT IS DELETED. The byte count is the only number that
	# separates "the frame was lost" from "nothing happened", and the `rm`
	# used to destroy it one line before it was needed.
	size=$(stat -c %s "${out}" 2>/dev/null || printf 0)
	rm -f "${out}"

	qa_log "${label}: gst-launch-1.0 rc=${rc} — DIAGNOSTIC ONLY, not the gate (BOARD-QUALIFICATION.md §11)"

	qa_assert_dmesg_count "${mark}" "hw_run failed: -${errnum}, failing task " 1 \
		"${label}: the worker reported the fault exactly once (hw_run failed: -${errnum})"
	qa_assert_dmesg_count "${mark}" "wait result ret -${QA_ERRNO_NUMBER[ENODEV]}([^0-9]|$)" 1 \
		"${label}: the waiter was told the task aborted exactly once (wait result ret -${QA_ERRNO_NUMBER[ENODEV]})"
	qa_assert_fault_stream_shorter "${label}" "${size}"

	(( QA_FAILURES == before ))
}

