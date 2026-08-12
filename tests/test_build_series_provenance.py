"""Provenance fixtures for scripts/build-series.py.

The lore-posting variant exists to make one claim impossible: that an unmerged
posting came from a commit. These tests pin that claim from both sides -- the
generated header must not carry an identity it does not have, and the pre-existing
merged-commit output must not have changed to make room for it.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import unittest
from dataclasses import replace
from pathlib import Path

from . import ROOT, load_script

bs = load_script("build-series.py", "ceralive_build_series_provenance")

MERGED_MARKER_RE = re.compile(r"^commit [0-9a-f]{40} upstream\.$", re.MULTILINE)
HEX40_DELIMITER_RE = re.compile(r"^From [0-9a-f]{40} ")

VALID_DIGESTS = ("a" * 64, "b" * 64, "c" * 64)

# The validator checks that canonical_mail exists and hashes to its recorded
# digest, so a fixture needs a real in-tree file. Any tracked file does; this one
# is chosen because it is always present in this lane.
STAND_IN_MAIL = "backports/README.md"
STAND_IN_MAIL_SHA256 = hashlib.sha256((ROOT / STAND_IN_MAIL).read_bytes()).hexdigest()
MERGED_FIXTURE_SOURCE = "0007-iommu-rockchip-disable-fetch-dte-time-limit.patch"


def pin() -> dict[str, str]:
    return bs.read_pin()


def header_of(text: str) -> str:
    return text.split("\n---\n", 1)[0]


def lore_members() -> list:
    return [p for p in bs.SERIES if p.origin == bs.BACKPORTS and p.lore is not None]


def merged_members() -> list:
    return [p for p in bs.SERIES if p.origin == bs.BACKPORTS and p.backport is not None]


def sample_lore(**overrides) -> bs.LorePosting:
    fields = {
        "lore_msgid": "posting@example.com",
        "revision": "v2",
        "posted_date": "Mon, 1 Jun 2026 12:00:00 +0000",
        "upstream_subject": "subsystem: do the thing",
        "thread_compressed_sha256": VALID_DIGESTS[0],
        "thread_mbox_sha256": VALID_DIGESTS[1],
        "canonical_patch_sha256": STAND_IN_MAIL_SHA256,
        "canonical_mail": STAND_IN_MAIL,
        "review_state": "posted, no review tags",
        "note": ("why this series carries it",),
    }
    fields.update(overrides)
    return bs.LorePosting(**fields)


def sample_patch(**overrides) -> bs.Patch:
    fields = {
        "filename": "0099-fixture.patch",
        "ordinal": 99,
        "subject": "subsystem: do the thing",
        "provenance": bs.LORE_POSTING,
        "author": "Author <author@example.com>",
        "date": "Mon, 1 Jun 2026 12:00:00 +0000",
        "origin": bs.BACKPORTS,
        "lore": sample_lore(),
    }
    fields.update(overrides)
    return bs.Patch(**fields)


class TestLoreHeadersClaimNoIdentity(unittest.TestCase):
    def test_a_rendered_lore_header_states_no_identity(self) -> None:
        rendered = bs.build_patch(
            sample_patch(filename=MERGED_FIXTURE_SOURCE), [], pin()
        )
        header = header_of(rendered)
        self.assertIsNone(MERGED_MARKER_RE.search(header))
        self.assertIsNone(HEX40_DELIMITER_RE.match(header.splitlines()[0]))
        self.assertNotIn(bs.NULL_OID, header)
        self.assertNotIn("ALREADY upstream", header)
        self.assertIn("Backport of unmerged v2 posting.", header)
        self.assertIn("no commit id exists for", header)

    def test_no_generated_lore_header_claims_a_commit(self) -> None:
        for patch in lore_members():
            with self.subTest(patch=patch.filename):
                header = header_of(
                    (ROOT / "patches" / patch.filename).read_text(encoding="utf-8")
                )
                self.assertIsNone(MERGED_MARKER_RE.search(header))
                self.assertIsNone(HEX40_DELIMITER_RE.match(header.splitlines()[0]))
                self.assertNotIn(bs.NULL_OID, header)
                self.assertNotIn("ALREADY upstream", header)
                self.assertIn(
                    f"Backport of unmerged {patch.lore.revision} posting.", header
                )
                self.assertIn(f"https://lore.kernel.org/r/{patch.lore.lore_msgid}", header)
                self.assertIn(patch.lore.review_state.split(";")[0], header)

    def test_each_digest_appears_under_its_own_name(self) -> None:
        for patch in lore_members():
            with self.subTest(patch=patch.filename):
                header = header_of(
                    (ROOT / "patches" / patch.filename).read_text(encoding="utf-8")
                )
                self.assertIn(
                    f"thread_compressed_sha256 {patch.lore.thread_compressed_sha256}",
                    header,
                )
                self.assertIn(
                    f"thread_mbox_sha256       {patch.lore.thread_mbox_sha256}", header
                )
                self.assertIn(
                    f"canonical_patch_sha256   {patch.lore.canonical_patch_sha256}",
                    header,
                )

    def test_canonical_mail_reproduces_its_digest(self) -> None:
        for patch in lore_members():
            with self.subTest(patch=patch.filename):
                mail = ROOT / patch.lore.canonical_mail
                self.assertTrue(mail.is_file(), mail)
                self.assertEqual(
                    hashlib.sha256(mail.read_bytes()).hexdigest(),
                    patch.lore.canonical_patch_sha256,
                )


class TestMergedOutputIsUnperturbed(unittest.TestCase):
    def test_merged_backport_still_claims_its_commit(self) -> None:
        for patch in merged_members():
            with self.subTest(patch=patch.filename):
                header = header_of(
                    (ROOT / "patches" / patch.filename).read_text(encoding="utf-8")
                )
                self.assertTrue(HEX40_DELIMITER_RE.match(header.splitlines()[0]))
                self.assertIn(f"commit {patch.provenance} upstream.", header)
                self.assertIn("ALREADY upstream", header)
                self.assertNotIn("Backport of unmerged", header)

    def test_adding_a_lore_sibling_does_not_change_merged_bytes(self) -> None:
        merged = merged_members()[0]
        before = bs.build_patch(merged, [], pin())
        original = bs.SERIES
        try:
            bs.SERIES = (*original, sample_patch())
            after = bs.build_patch(merged, [], pin())
        finally:
            bs.SERIES = original
        self.assertEqual(before, after)

    def test_generated_tree_matches_what_the_generator_produces(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build-series.py"), "--check"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class TestProvenanceValidation(unittest.TestCase):
    def assertRejects(self, patch: bs.Patch, needle: str) -> None:
        problems = bs.validate_backports_entry(patch, "fixture")
        self.assertTrue(problems, "expected a rejection, got none")
        self.assertTrue(
            any(needle in problem for problem in problems),
            f"{needle!r} not in {problems}",
        )

    def test_a_well_formed_lore_entry_is_accepted(self) -> None:
        self.assertEqual(bs.validate_backports_entry(sample_patch(), "fixture"), [])

    def test_lore_entry_may_not_carry_a_commit_id(self) -> None:
        self.assertRejects(sample_patch(provenance="0" * 39 + "1"), "must be exactly")

    def test_lore_entry_may_not_carry_null_oid(self) -> None:
        self.assertRejects(sample_patch(provenance=bs.NULL_OID), "must be exactly")

    def test_mixed_provenance_is_rejected(self) -> None:
        mixed = sample_patch(
            backport=bs.Backport(
                upstream_subject="s", lore_msgid="m@example.com", note=("n",)
            )
        )
        self.assertRejects(mixed, "mutually exclusive origins")

    def test_backports_entry_with_no_provenance_at_all(self) -> None:
        self.assertRejects(
            sample_patch(lore=None, provenance="d" * 40), "must name its own origin"
        )

    def test_every_lore_field_is_mandatory(self) -> None:
        for field in (
            "lore_msgid",
            "revision",
            "posted_date",
            "upstream_subject",
            "thread_compressed_sha256",
            "thread_mbox_sha256",
            "canonical_patch_sha256",
            "canonical_mail",
            "review_state",
        ):
            with self.subTest(field=field):
                self.assertRejects(
                    sample_patch(lore=sample_lore(**{field: "  "})),
                    f"LorePosting.{field} is mandatory",
                )

    def test_note_is_mandatory(self) -> None:
        self.assertRejects(
            sample_patch(lore=sample_lore(note=())), "LorePosting.note is mandatory"
        )

    def test_conflated_thread_digests_are_rejected(self) -> None:
        self.assertRejects(
            sample_patch(
                lore=sample_lore(thread_mbox_sha256=VALID_DIGESTS[0])
            ),
            "different domains",
        )

    def test_non_sha256_digest_is_rejected(self) -> None:
        self.assertRejects(
            sample_patch(lore=sample_lore(thread_mbox_sha256="not-a-digest")),
            "is not a sha256 digest",
        )

    def test_revision_must_look_like_a_revision(self) -> None:
        self.assertRejects(
            sample_patch(lore=sample_lore(revision="third")), "is not a vN revision"
        )

    def test_missing_canonical_mail_is_rejected(self) -> None:
        self.assertRejects(
            sample_patch(lore=sample_lore(canonical_mail="backports/lore/none.mbox")),
            "is missing",
        )

    def test_canonical_mail_digest_mismatch_is_rejected(self) -> None:
        self.assertRejects(
            sample_patch(lore=sample_lore(canonical_patch_sha256=VALID_DIGESTS[2])),
            "hashes to",
        )

    def test_lore_provenance_outside_the_backports_lane_is_rejected(self) -> None:
        original = bs.SERIES
        try:
            bs.SERIES = (
                replace(
                    sample_patch(),
                    origin=bs.CERALIVE,
                    rationale=("first party",),
                    provenance=bs.NULL_OID,
                ),
            )
            problems = bs.validate_series()
        finally:
            bs.SERIES = original
        self.assertTrue(
            any("only the backports/ lane carries a LorePosting" in p for p in problems),
            problems,
        )

    def test_the_real_series_validates(self) -> None:
        self.assertEqual(bs.validate_series(), [])


if __name__ == "__main__":
    unittest.main()
