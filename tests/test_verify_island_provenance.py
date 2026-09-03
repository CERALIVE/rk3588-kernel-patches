from __future__ import annotations

import ast
import hashlib
import io
import shutil
import tarfile
import tempfile
import unittest
from pathlib import Path

from tests import ROOT, load_script

verifier = load_script(
    "verify-island-provenance.py", "ceralive_verify_island_provenance"
)


class TestIslandReleaseVerifier(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.lane = self.root / "island"
        shutil.copytree(ROOT / "island", self.lane)
        self.asset = self.root / verifier.ASSET
        with tarfile.open(self.asset, mode="w") as archive:
            for asset_member, lane_member in verifier.MEMBERS:
                data = (self.lane / lane_member).read_bytes()
                info = tarfile.TarInfo(asset_member)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
        self.original_sha256 = verifier.ASSET_SHA256
        verifier.ASSET_SHA256 = hashlib.sha256(self.asset.read_bytes()).hexdigest()

    def tearDown(self) -> None:
        verifier.ASSET_SHA256 = self.original_sha256
        self.temporary.cleanup()

    def test_matching_lane_passes(self) -> None:
        self.assertEqual(verifier.verify(self.asset, self.lane), [])

    def test_flipped_member_byte_fails_by_name(self) -> None:
        victim = self.lane / verifier.MEMBERS[0][1]
        data = bytearray(victim.read_bytes())
        data[-1] ^= 1
        victim.write_bytes(data)
        problems = verifier.verify(self.asset, self.lane)
        self.assertTrue(any(victim.name in problem for problem in problems), problems)

    def test_wrong_asset_digest_fails_before_member_comparison(self) -> None:
        verifier.ASSET_SHA256 = "0" * 64
        problems = verifier.verify(self.asset, self.lane)
        self.assertEqual(len(problems), 1)
        self.assertIn("sha256", problems[0])

    def test_verifier_does_not_import_build_series(self) -> None:
        source = (ROOT / "scripts" / "verify-island-provenance.py").read_text()
        tree = ast.parse(source)
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertNotIn("build-series", imported)


if __name__ == "__main__":
    unittest.main()
