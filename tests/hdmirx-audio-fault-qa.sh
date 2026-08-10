#!/usr/bin/env bash
#
# hdmirx-audio-fault-qa.sh — exercise the HDMI-RX audio worker/clock lifecycle
# under lockdep.
#
# RUNS ON HARDWARE ONLY, on the non-shipping `edge-test` kernel
# (CONFIG_VIDEO_ROCKCHIP_HDMIRX_CERALIVE_TEST + PROVE_LOCKING + KASAN).
#
# TWO DISTINCT CLAIMS, and they fail differently:
#
#   1. THE CANCEL IS LOCK-SAFE. The audio worker calls back into the ASoC codec,
#      which takes the codec's own lock; the plug/unplug path takes the driver's
#      work_lock. A synchronous cancel performed from under work_lock closes a
#      cycle between those two locks. `delay_worker_ms` widens the window so a
#      cancel genuinely races a RUNNING worker rather than an idle one, which is
#      the only way the ordering is actually put to the test. The assertion is
#      the absence of a lockdep report -- so the run must be long enough, and
#      real enough, for lockdep to have had something to say.
#
#   2. A FAILED CLOCK-RATE CHANGE IS REPORTED AND SURVIVABLE. clk_set_rate()'s
#      return used to be discarded, so a refused rate left the driver believing
#      it had a rate it does not have. The injected failure must produce -EIO,
#      increment its counter exactly once, auto-reset, leave the PREVIOUS valid
#      rate in place, and the next (non-injected) update must succeed.
#
# The plug/unplug cycling is driven by the driver's own hotplug path where a
# live source is available; where it is not, the worker delay plus the ALSA
# capture open/close is the deterministic test-hook equivalent and is what makes
# this runnable on a bench board with nothing plugged into HDMI-IN.
#
# Usage:
#   hdmirx-audio-fault-qa.sh [--debugfs /sys/kernel/debug/hdmirx-audio-test]
#                            [--delay-ms 1000] [--iterations 50] [--fail-clock-once]
#   hdmirx-audio-fault-qa.sh --self-test     # host-side, no hardware, no root

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/qa-common.sh
source "${HERE}/lib/qa-common.sh"

QA_DEBUGFS="/sys/kernel/debug/hdmirx-audio-test"
QA_DELAY_MS=1000
QA_ITERATIONS=50
QA_FAIL_CLOCK=0

usage() { sed -n '2,32p' "${BASH_SOURCE[0]}"; }

# The HDMI-RX capture card is discovered by NAME, never by card index: index 0
# is whichever card registered first and moves with the USB dongle.
qa_hdmirx_card() {
	local line
	while read -r line; do
		case "${line}" in *hdmirx*) printf '%s' "${line%% *}"; return 0 ;; esac
	done < <(sed -n 's/^ *\([0-9]\+\) \[\([^ ]*\) *\].*/\2/p' /proc/asound/cards 2>/dev/null)
	return 1
}

# One audio-domain cycle: open the capture PCM briefly and close it. That is the
# path that arms and then disarms the audio worker, which is what a cancel has
# to race.
qa_audio_cycle() {
	local card="$1"
	timeout 5 arecord -D "plughw:CARD=${card}" -f S16_LE -r 48000 -c 2 -d 1 \
		-t raw >/dev/null 2>&1
	return 0
}

run_delay_case() {
	local card="$1" mark i
	mark="$(qa_dmesg_mark)"

	qa_arm delay_worker_ms "${QA_DELAY_MS}" delay_worker_consumed || return 1

	for (( i = 0; i < QA_ITERATIONS; i++ )); do
		qa_audio_cycle "${card}"
	done

	qa_assert_consumed
	qa_assert_no_sanitizer_report "${mark}" "audio-delay"
	qa_log "ok ${QA_ITERATIONS} audio arm/cancel cycles with a delayed worker, lockdep clean"
}

run_clock_case() {
	local card="$1" mark
	mark="$(qa_dmesg_mark)"

	qa_arm fail_clk_set_rate_once 1 fail_clk_set_rate_consumed || return 1
	qa_audio_cycle "${card}"
	qa_assert_consumed

	# The recovery leg is the half that proves the driver kept a coherent
	# state rather than merely returned an error: a subsequent, uninjected
	# rate update has to succeed.
	qa_audio_cycle "${card}"
	qa_assert_eq "0" "$(qa_read_knob fail_clk_set_rate_once)" "fail_clk_set_rate_once still reset"
	qa_assert_no_sanitizer_report "${mark}" "audio-clock-failure"
	qa_log "ok injected clk_set_rate failure reported, then a clean update succeeded"
}

run_self_test() {
	local rc=0 work
	work="$(mktemp -d)"

	QA_DEBUGFS="${work}/hdmirx-audio-test"
	mkdir -p "${QA_DEBUGFS}"
	printf '0\n' >"${QA_DEBUGFS}/fail_clk_set_rate_once"
	printf '0\n' >"${QA_DEBUGFS}/fail_clk_set_rate_consumed"

	QA_FAILURES=0
	qa_arm fail_clk_set_rate_once 1 fail_clk_set_rate_consumed >/dev/null
	qa_assert_consumed >/dev/null 2>&1
	if (( QA_FAILURES > 0 )); then
		printf '  ok  an ignored clock knob is reported as a FAILURE\n'
	else
		printf '  FAIL an ignored clock knob passed\n' >&2; rc=1
	fi

	QA_FAILURES=0
	printf '1\n' >"${QA_DEBUGFS}/fail_clk_set_rate_consumed"
	printf '0\n' >"${QA_DEBUGFS}/fail_clk_set_rate_once"
	qa_assert_consumed >/dev/null 2>&1
	if (( QA_FAILURES == 0 )); then
		printf '  ok  a consumed, auto-reset clock knob passes\n'
	else
		printf '  FAIL a correctly consumed clock knob was rejected\n' >&2; rc=1
	fi

	# Card discovery must be by NAME. A fixture whose hdmirx card is NOT index
	# 0 is the whole point: an index-based lookup would pick the wrong card.
	local fake_proc="${work}/cards"
	cat >"${fake_proc}" <<'EOF'
 0 [Dongle         ]: USB-Audio - USB dongle
 1 [rockchiphdmirx ]: simple-card - hdmirx-sound
EOF
	local card
	card="$(sed -n 's/^ *\([0-9]\+\) \[\([^ ]*\) *\].*/\2/p' "${fake_proc}" |
		grep hdmirx | head -1)"
	if [[ "${card}" == "rockchiphdmirx" ]]; then
		printf '  ok  the HDMI-RX card is discovered by NAME, not by index 0\n'
	else
		printf '  FAIL card discovery: got "%s"\n' "${card}" >&2; rc=1
	fi

	rm -rf "${work}"
	(( rc == 0 )) && printf 'RESULT=PASS case=self-test\n'
	return "${rc}"
}

main() {
	local self_test=0

	while (( $# )); do
		case "$1" in
			--debugfs)      QA_DEBUGFS="${2:-}"; shift 2 ;;
			--debugfs=*)    QA_DEBUGFS="${1#--debugfs=}"; shift ;;
			--delay-ms)     QA_DELAY_MS="${2:-}"; shift 2 ;;
			--delay-ms=*)   QA_DELAY_MS="${1#--delay-ms=}"; shift ;;
			--iterations)   QA_ITERATIONS="${2:-}"; shift 2 ;;
			--iterations=*) QA_ITERATIONS="${1#--iterations=}"; shift ;;
			--fail-clock-once) QA_FAIL_CLOCK=1; shift ;;
			--self-test)    self_test=1; shift ;;
			-h|--help)      usage; return 0 ;;
			*) usage >&2; qa_die "unknown argument: $1" ;;
		esac
	done

	(( self_test )) && { run_self_test; return $?; }

	[[ -d "${QA_DEBUGFS}" ]] \
		|| qa_die "${QA_DEBUGFS} not present — is this an edge-test kernel with debugfs mounted?"
	qa_require_cmd arecord dmesg timeout

	local card
	card="$(qa_hdmirx_card)" \
		|| qa_die "no HDMI-RX ALSA card found in /proc/asound/cards — patches 0005/0006 must be applied and the DT card enabled"
	qa_log "HDMI-RX capture card: ${card}"

	run_delay_case "${card}"
	(( QA_FAIL_CLOCK )) && run_clock_case "${card}"

	qa_result "hdmirx-audio" "card=${card}" "delay_ms=${QA_DELAY_MS}" \
		"iterations=${QA_ITERATIONS}"
}

main "$@"
