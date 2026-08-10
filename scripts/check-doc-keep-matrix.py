#!/usr/bin/env python3
"""check-doc-keep-matrix.py — assert every maintained doc still carries its
required evidence markers.

Wave 7 (pipeline-restructure-kernel-backports, todo38) tool. Loads
`.omo/evidence/pipeline-restructure-kernel-backports/wave7/keep-matrix.yaml`
and, for every file it lists, asserts every required marker string is present
verbatim in that file's current contents — both BEFORE a trim (to freeze the
baseline) and AFTER (to prove nothing load-bearing was cut). A marker is a
literal substring, not a regex: the matrix's job is to catch deletion of a
fact (a date, a Message-ID, a SHA, a retire trigger, an N/A leg, a run ID),
not to freeze prose wording around it.

No third-party dependencies — the YAML subset used by keep-matrix.yaml (a
top-level `files:` map of `<path>: {required: [str, ...]}`) is parsed by a
small hand-rolled reader so this script runs with stdlib only, matching the
rest of this repository's Python tooling.

Exit codes: 0 pass, 1 missing marker(s) or file(s), 2 usage/matrix error.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


class MatrixError(Exception):
    """Malformed matrix file — exit 2."""


def _dequote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def parse_matrix(path: Path) -> dict[str, list[str]]:
    """Minimal parser for keep-matrix.yaml's specific shape:

        files:
          <relative/path>:
            required:
              - "marker one"
              - "marker two"

    Comments (`#`) and blank lines are ignored. Indentation is 2 spaces per
    level, matching the file this script ships beside.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise MatrixError(f"cannot read matrix file {path}: {exc}") from exc

    lines = [ln for ln in raw.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    if not lines or lines[0].strip() != "files:":
        raise MatrixError("matrix file must start with a top-level 'files:' key")

    result: dict[str, list[str]] = {}
    current_file: str | None = None
    in_required = False
    for ln in lines[1:]:
        indent = len(ln) - len(ln.lstrip(" "))
        stripped = ln.strip()
        if indent == 2 and stripped.endswith(":") and stripped != "required:":
            current_file = _dequote(stripped[:-1])
            result[current_file] = []
            in_required = False
            continue
        if indent == 4 and stripped == "required:":
            if current_file is None:
                raise MatrixError("'required:' block with no preceding file key")
            in_required = True
            continue
        if indent >= 6 and stripped.startswith("- "):
            if not in_required or current_file is None:
                raise MatrixError(f"marker line outside a required: block: {ln!r}")
            result[current_file].append(_dequote(stripped[2:]))
            continue
        raise MatrixError(f"unrecognized matrix line: {ln!r}")

    if not result:
        raise MatrixError("matrix file declares no files")
    for fname, markers in result.items():
        if not markers:
            raise MatrixError(f"{fname}: 'required:' list is empty — a doc with no markers is unprotected")
    return result


def check(matrix_path: Path, root: Path, out=sys.stdout) -> int:
    try:
        matrix = parse_matrix(matrix_path)
    except MatrixError as exc:
        print(f"MATRIX ERROR: {exc}", file=out)
        return 2

    total_missing = 0
    total_files_ok = 0
    for rel_path, markers in matrix.items():
        doc_path = root / rel_path
        if not doc_path.is_file():
            print(f"MISSING FILE  {rel_path}", file=out)
            total_missing += 1
            continue
        content = doc_path.read_text(encoding="utf-8")
        file_missing = [m for m in markers if m not in content]
        if file_missing:
            for m in file_missing:
                print(f"MISSING MARKER  {rel_path}  :: {m!r}", file=out)
            total_missing += len(file_missing)
        else:
            total_files_ok += 1

    print(
        f"---- files={len(matrix)} ok={total_files_ok} "
        f"missing_files={sum(1 for r in matrix if not (root / r).is_file())} "
        f"missing_markers={total_missing}",
        file=out,
    )
    if total_missing:
        print(f"RESULT: FAIL — {total_missing} missing marker(s)/file(s)", file=out)
        return 1
    print(f"RESULT: PASS — {len(matrix)} file(s), every required marker present", file=out)
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        prog="check-doc-keep-matrix.py",
        description="Assert every maintained doc still carries its required evidence markers.",
    )
    ap.add_argument("--matrix", required=True, help="path to keep-matrix.yaml")
    ap.add_argument("--root", required=True, help="repository root the matrix's paths are relative to")
    args = ap.parse_args(argv)
    return check(Path(args.matrix), Path(args.root))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
