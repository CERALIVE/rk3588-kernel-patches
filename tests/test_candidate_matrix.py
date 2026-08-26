from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from tests import ROOT

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SOURCE_SHA256 = "0" * 64


class TestDeferredDisposition(unittest.TestCase):
    def run_validator(self, fixture: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "validate-candidate-matrix.py"),
                str(FIXTURES / fixture),
                "--aliases",
                "N12",
                "--source-sha256",
                SOURCE_SHA256,
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_deferred_row_with_failed_route_and_attempt_date_passes(self) -> None:
        result = self.run_validator("candidate-matrix-deferred-valid.md")

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_deferred_row_without_failed_route_and_attempt_date_fails(self) -> None:
        result = self.run_validator("candidate-matrix-deferred-missing-route-date.md")

        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("failed route", result.stderr)
        self.assertIn("attempt date", result.stderr)
