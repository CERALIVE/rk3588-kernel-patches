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
	local dir="$1" commit="${2:-8d3ae59288f1e7d58d76558a6ee96d533bc5019f}" patchdir="${3:-patch/kernel/archive/rockchip64-7.2}" armbian_revision="${4:-pinned-revision}"
	mkdir -p "${dir}"
	cat >"${dir}/kernel-pin.env" <<EOF
KERNEL_TAG="v7.2"
KERNEL_COMMIT="${commit}"
KERNEL_PATCHDIR="${patchdir}"
KERNELSOURCE="https://example.invalid/linux.git"
ARMBIAN_BUILD_REV="${armbian_revision}"
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
	case "${MOCK_ARMBIAN_MODE:-no-drift}" in
	no-drift)
		cat >"${destination}" <<'MAP'
bleedingedge)
    KERNEL_MAJOR_MINOR="7.2"
    LINUXFAMILY=rockchip64
    ;;
MAP
		;;
	drift)
		cat >"${destination}" <<'MAP'
bleedingedge)
    KERNEL_MAJOR_MINOR="7.3"
    LINUXFAMILY=rockchip64-next
    ;;
MAP
		;;
	*) : >"${destination}" ;;
	esac
fi
EOF
chmod +x "${dir}/scripts/curl"
}

run_case() {
	local name="$1" expected="$2" mode="${3:-ok}" commit="${4:-8d3ae59288f1e7d58d76558a6ee96d533bc5019f}" patchdir="${5:-patch/kernel/archive/rockchip64-7.2}" armbian_mode="${6:-no-drift}" armbian_revision="${7:-pinned-revision}" expected_output="${8:-}"
	local dir="${tmp}/${name}"
	make_pin "${dir}" "${commit}" "${patchdir}" "${armbian_revision}"
	if MOCK_GIT_MODE="${mode}" MOCK_RESOLVED_COMMIT="8d3ae59288f1e7d58d76558a6ee96d533bc5019f" \
		MOCK_ARMBIAN_MODE="${armbian_mode}" \
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
	if [[ -n "${expected_output}" ]] && ! grep -Fq "${expected_output}" "${tmp}/${name}.out"; then
		printf 'FAIL %s: expected output %s\n' "${name}" "${expected_output}" >&2
		cat "${tmp}/${name}.out" >&2
		return 1
	fi
	printf 'PASS %s\n' "${name}"
}

# Armbian mapping observations are distinct: the pinned revision agrees with
# the selected alias in one case, while a drifted revision reports 7.3 in the
# other. Neither observation can block the sovereign pin.
run_case no-drift 0 ok '' '' no-drift pinned-revision 'KERNEL_MAJOR_MINOR 7.2'
run_case drifted-upstream 0 ok '' '' drift drifted-revision 'KERNEL_MAJOR_MINOR 7.3'
# Local coordinates remain a blocking contract.
run_case inconsistent-patchdir 1 ok '' patch/kernel/archive/rockchip64-7.3
run_case unresolvable-commit 1 unresolvable

# Exercise the real apply gate against a clean fake kernel tree whose v7.2 tag
# does not match the broken commit pin. The apply script must reject it before
# applying any patch.
apply_fixture="${tmp}/apply-repo"
GIT_MASTER=1 git -C "${ROOT}" worktree add --detach "${apply_fixture}" HEAD >/dev/null
cleanup_apply_fixture() { GIT_MASTER=1 git -C "${ROOT}" worktree remove --force "${apply_fixture}" >/dev/null 2>&1 || true; }
trap 'cleanup_apply_fixture; rm -rf "${tmp}"' EXIT
python3 - "${apply_fixture}/kernel-pin.env" <<'PY'
from pathlib import Path
import sys

pin = Path(sys.argv[1])
text = pin.read_text()
text = text.replace(
    'KERNEL_COMMIT="8d3ae59288f1e7d58d76558a6ee96d533bc5019f"',
    'KERNEL_COMMIT="deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"',
)
pin.write_text(text)
PY
# Keep the apply test focused on its real pin-verification path. The copied
# fixture's series/provenance checks are covered by the blocking CI jobs and
# otherwise require the published island asset before this failure is reached.
for helper in build-series.py verify-payload-parity.py verify-island-provenance.py; do
	cat >"${apply_fixture}/scripts/${helper}" <<'PY'
#!/usr/bin/env python3
raise SystemExit(0)
PY
done
fake_kernel="${tmp}/fake-kernel"
mkdir -p "${fake_kernel}"
(cd "${fake_kernel}" && GIT_MASTER=1 git init -q && GIT_MASTER=1 git config user.name test && GIT_MASTER=1 git config user.email test@example.invalid && touch placeholder && GIT_MASTER=1 git add placeholder && GIT_MASTER=1 git commit -q -m initial && GIT_MASTER=1 git tag -a v7.2 -m v7.2)
if (cd "${apply_fixture}" && scripts/apply.sh "${fake_kernel}") >"${tmp}/apply-failure.out" 2>&1; then
	echo "FAIL apply-verification-failure: apply.sh unexpectedly succeeded" >&2
	cat "${tmp}/apply-failure.out" >&2
	exit 1
fi
grep -Fq 'but kernel-pin.env pins deadbeefdeadbeefdeadbeefdeadbeefdeadbeef' "${tmp}/apply-failure.out"
echo 'PASS apply-verification-failure'
