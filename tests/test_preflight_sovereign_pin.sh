#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${ROOT}/scripts/preflight.sh"
tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT

cat >"${tmp}/git" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${MOCK_GIT_MODE:-ok}" == unresolvable ]]; then
	exit 0
fi
printf '%s refs/tags/v7.2^{}\n' "${MOCK_RESOLVED_COMMIT}"
EOF
chmod +x "${tmp}/git"

make_pin() {
	local dir="$1" commit="${2:-8d3ae59288f1e7d58d76558a6ee96d533bc5019f}" patchdir="${3:-patch/kernel/archive/rockchip64-7.2}"
	mkdir -p "${dir}"
	cat >"${dir}/kernel-pin.env" <<EOF
KERNEL_TAG="v7.2"
KERNEL_COMMIT="${commit}"
KERNEL_PATCHDIR="${patchdir}"
KERNELSOURCE="https://example.invalid/linux.git"
ARMBIAN_BUILD_REV="drifted-revision"
ARMBIAN_BRANCH="bleedingedge"
EOF
	mkdir -p "${dir}/scripts"
	cp "${SCRIPT}" "${dir}/scripts/preflight.sh"
	cat >"${dir}/scripts/curl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
destination=""
for ((i = 1; i <= $#; i++)); do
	if [[ "${!i}" == -o ]]; then
		next=$((i + 1))
		destination="${!next}"
	fi
done
if [[ -n "${destination}" ]]; then
	: >"${destination}"
fi
EOF
chmod +x "${dir}/scripts/curl"
}

run_case() {
	local name="$1" expected="$2" mode="${3:-ok}" commit="${4:-8d3ae59288f1e7d58d76558a6ee96d533bc5019f}" patchdir="${5:-patch/kernel/archive/rockchip64-7.2}"
	local dir="${tmp}/${name}"
	make_pin "${dir}" "${commit}" "${patchdir}"
	if MOCK_GIT_MODE="${mode}" MOCK_RESOLVED_COMMIT="8d3ae59288f1e7d58d76558a6ee96d533bc5019f" \
		PATH="${tmp}:${dir}/scripts:${PATH}" "${dir}/scripts/preflight.sh" >"${tmp}/${name}.out" 2>&1; then
		actual=0
	else
		actual=$?
	fi
	[[ "${actual}" == "${expected}" ]] || {
		printf 'FAIL %s: expected exit %s, got %s\n' "${name}" "${expected}" "${actual}" >&2
		cat "${tmp}/${name}.out" >&2
		return 1
	}
	printf 'PASS %s\n' "${name}"
}

# Armbian drift of any amount is informational and cannot block the sovereign pin.
run_case drifted-upstream 0
# Local coordinates remain a blocking contract.
run_case inconsistent-patchdir 1 ok '' patch/kernel/archive/rockchip64-7.3
run_case unresolvable-commit 1 unresolvable
run_case apply-verification-failure 1 ok deadbeefdeadbeefdeadbeefdeadbeefdeadbeef
run_case no-drift 0
