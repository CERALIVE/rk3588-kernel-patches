#!/usr/bin/env bash
#
# qa-fixture.sh — a synthetic debugfs, shaped like the real one.
#
# WHY THIS EXISTS. The fault harnesses read debugfs nodes that only exist on a
# board booted into the `edge-test` kernel, so until now the only way to find out
# whether they read the RIGHT node names was to spend a board session finding
# out. That is exactly how the wrong `*_consumed` names survived review: the
# self-tests built their own fixture inline, from the same wrong names the
# harness used, so the two agreed with each other and neither agreed with the
# driver.
#
# So the fixture is built from ONE source — the fault-control table in
# qa-common.sh, which qa_verify_controls_against_patches re-derives from the
# driver sources. A fixture cannot contain a node the driver does not create,
# and a harness that asks for a name outside the table gets nothing to read.
#
# WHAT IT SIMULATES. The driver's one-shot semantics, and only those:
#
#   armed knob + consume  ->  counter += 1, knob := 0   (the fault fired once)
#   unarmed knob + consume ->  nothing                  (nothing to fire)
#
# It deliberately does NOT simulate an encode, a bind, or an ALSA cycle. This is
# a fixture for the harness's BOOKKEEPING, not a fake driver, and a fixture that
# pretended to be a driver would start being trusted as one.
#
# shellcheck shell=bash

# qa_fixture_make <dir> <driver> — a debugfs-shaped directory for <driver>.
qa_fixture_make() {
	local dir="$1" driver="$2" node
	mkdir -p "${dir}"
	while read -r node; do
		[[ -n "${node}" ]] || continue
		printf '0\n' >"${dir}/${node}"
	done < <(qa_controls_for "${driver}")
}

# qa_fixture_consume <dir> <driver> <knob> — what a correct driver does when the
# instrumented path is reached.
qa_fixture_consume() {
	local dir="$1" driver="$2" knob="$3" counter armed
	counter="${QA_FAULT_COUNTER[${driver}:${knob}]}"
	armed="$(<"${dir}/${knob}")"
	(( armed == 0 )) && return 1
	printf '%s\n' "$(( $(<"${dir}/${counter}") + 1 ))" >"${dir}/${counter}"
	printf '0\n' >"${dir}/${knob}"
	return 0
}

# qa_fixture_consume_twice — the other way a driver can be wrong. A counter that
# moves by two is as much a defect as one that never moves, and the harness must
# say so.
qa_fixture_consume_twice() {
	local dir="$1" driver="$2" knob="$3" counter
	counter="${QA_FAULT_COUNTER[${driver}:${knob}]}"
	qa_fixture_consume "${dir}" "${driver}" "${knob}" || return 1
	printf '%s\n' "$(( $(<"${dir}/${counter}") + 1 ))" >"${dir}/${counter}"
}
