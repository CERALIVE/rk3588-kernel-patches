from __future__ import annotations

import re
import subprocess
import sys
import unittest
from dataclasses import replace

from tests import ROOT, load_script

bs = load_script("build-series.py", "ceralive_build_series_island")

RELEASE_TAG = "v2026.9.2"
RELEASE_COMMIT = "1fd357d8a8b83b6f4ed7f7692d761f7b653d44f5"
RELEASE_ASSET_SHA256 = (
    "393b50a26117b95659f35a603abb9939f767e397f71e85fb180dda107e2df616"
)
SOURCE_FIXTURE = "0031-rk3588-media-island-drivers.patch"
MERGED_MARKER_RE = re.compile(r"^commit [0-9a-f]{40} upstream\.$", re.MULTILINE)
HEX40_DELIMITER_RE = re.compile(r"^From [0-9a-f]{40} ")


def sample_island(**overrides: str) -> bs.Island:
    fields = {
        "tag": RELEASE_TAG,
        "commit": RELEASE_COMMIT,
        "asset_sha256": RELEASE_ASSET_SHA256,
    }
    fields.update(overrides)
    return bs.Island(**fields)


def sample_patch(**overrides) -> bs.Patch:
    fields = {
        "filename": SOURCE_FIXTURE,
        "ordinal": 31,
        "subject": "video: rockchip: add the CeraLive RK3588 media island",
        "provenance": sample_island(),
        "author": "CeraLive <dev@ceralive.tv>",
        "date": "Wed, 2 Sep 2026 00:00:00 +0000",
        "origin": bs.ISLAND,
    }
    fields.update(overrides)
    return bs.Patch(**fields)


def island_members() -> list[bs.Patch]:
    return [patch for patch in bs.SERIES if patch.origin == bs.ISLAND]


class TestIslandProvenance(unittest.TestCase):
    def assert_rejected(self, patch: bs.Patch, needle: str) -> None:
        problems = bs.validate_island_entry(patch, "fixture")
        self.assertTrue(problems)
        self.assertTrue(any(needle in problem for problem in problems), problems)

    def test_real_members_name_the_published_release(self) -> None:
        members = island_members()
        self.assertEqual([patch.ordinal for patch in members], list(range(31, 40)))
        for patch in members:
            with self.subTest(patch=patch.filename):
                self.assertEqual(patch.provenance, sample_island())

    def test_header_names_release_without_claiming_kernel_commit(self) -> None:
        header = bs.build_patch(sample_patch(), [], bs.read_pin()).split("\n---\n", 1)[0]
        self.assertIsNone(MERGED_MARKER_RE.search(header))
        self.assertIsNone(HEX40_DELIMITER_RE.match(header.splitlines()[0]))
        self.assertNotIn(bs.NULL_OID, header)
        self.assertIn(
            f"Generated from CeraLive rk3588-media-island {RELEASE_TAG} "
            f"({RELEASE_COMMIT})",
            header,
        )
        self.assertIn(f"asset_sha256  {RELEASE_ASSET_SHA256}", header)

    def test_island_and_40_hex_provenance_are_refused(self) -> None:
        mixed = (sample_island(), RELEASE_COMMIT)
        self.assert_rejected(sample_patch(provenance=mixed), "mixed Island/string")

    def test_string_provenance_is_refused(self) -> None:
        self.assert_rejected(
            sample_patch(provenance=RELEASE_COMMIT), "provenance=Island"
        )

    def test_every_release_field_is_mandatory(self) -> None:
        for field in ("tag", "commit", "asset_sha256"):
            with self.subTest(field=field):
                self.assert_rejected(
                    sample_patch(provenance=sample_island(**{field: "  "})),
                    f"Island.{field} is mandatory",
                )

    def test_release_field_shapes_are_checked(self) -> None:
        self.assert_rejected(
            sample_patch(provenance=sample_island(tag="latest")), "vYYYY.M.P"
        )
        self.assert_rejected(
            sample_patch(provenance=sample_island(commit="dcda1a2")), "40-hex"
        )
        self.assert_rejected(
            sample_patch(provenance=sample_island(asset_sha256="bad")), "sha256"
        )

    def test_a_partial_release_update_is_refused(self) -> None:
        original = bs.SERIES
        first = island_members()[0]
        # Derived, never literal: a hardcoded tag silently stops being a mutation
        # the release it names ships, and the test then proves nothing.
        other_tag = f"{RELEASE_TAG}-not-the-shipped-tag"
        changed = replace(first, provenance=replace(first.provenance, tag=other_tag))
        try:
            bs.SERIES = tuple(
                changed if patch.filename == first.filename else patch
                for patch in original
            )
            problems = bs.validate_series()
        finally:
            bs.SERIES = original
        self.assertTrue(any("more than one island release" in p for p in problems))

    def test_island_provenance_outside_island_lane_is_refused(self) -> None:
        original = bs.SERIES
        try:
            bs.SERIES = (replace(sample_patch(), origin=bs.CERALIVE),)
            problems = bs.validate_series()
        finally:
            bs.SERIES = original
        self.assertTrue(any("only the island/ lane" in p for p in problems), problems)


class TestSlotAndMembershipInvariants(unittest.TestCase):
    def test_series_total_is_the_highest_slot_not_member_count(self) -> None:
        self.assertEqual(bs.SERIES_TOTAL, max(patch.ordinal for patch in bs.SERIES))
        self.assertGreater(bs.SERIES_TOTAL, len(bs.SERIES))

    def test_ordinal_above_series_total_is_refused(self) -> None:
        original = bs.SERIES
        try:
            bs.SERIES = (*original, sample_patch(ordinal=bs.SERIES_TOTAL + 1))
            problems = bs.validate_series()
        finally:
            bs.SERIES = original
        self.assertTrue(any("exceeds SERIES_TOTAL" in p for p in problems), problems)

    def test_retired_ordinals_stay_burned(self) -> None:
        carried = {patch.ordinal for patch in bs.SERIES}
        for entry in bs.load_retired().values():
            if entry.ordinal is not None:
                self.assertNotIn(entry.ordinal, carried)

    def test_real_tree_is_accounted_for(self) -> None:
        bs.check_membership(bs.load_retired())

    def test_build_series_check_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build-series.py"), "--check"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_island_member_is_never_reanchored(self) -> None:
        rule = bs.Rule(
            patch=SOURCE_FIXTURE,
            op="replace",
            anchor="\tvdec0: video-codec@fdc38000 {",
            payload="\tvdec0: video-codec@fdc38000 {",
            lineno=1,
        )
        with self.assertRaises(bs.RebaseError) as caught:
            bs.build_patch(sample_patch(), [rule], bs.read_pin())
        self.assertIn("never re-anchored", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
