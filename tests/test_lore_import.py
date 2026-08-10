"""Fixtures for scripts/import-lore-series.py.

Every screening refusal the importer can reach has a fixture here, because the
refusals are the feature: an importer that quietly picks a survivor out of an
ambiguous thread produces a patch nobody can trace back to a posting.
"""

from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from . import load_script

lore = load_script("import-lore-series.py", "ceralive_import_lore_series")

DIFF = (
    "diff --git a/drivers/x/y.c b/drivers/x/y.c\n"
    "--- a/drivers/x/y.c\n"
    "+++ b/drivers/x/y.c\n"
    "@@ -1,3 +1,3 @@\n"
    " context\n"
    "-old line\n"
    "+new line\n"
)

OTHER_DIFF = DIFF.replace("new line", "other line")

DATE = "Mon, 1 Jun 2026 12:00:00 +0000"


def message(
    msgid: str,
    subject: str,
    body: str,
    sender: str = "Author <author@example.com>",
    date: str = DATE,
    with_msgid: bool = True,
) -> str:
    head = [f"From nobody {date}"]
    if with_msgid:
        head.append(f"Message-ID: <{msgid}>")
    head += [f"From: {sender}", f"Subject: {subject}", f"Date: {date}", ""]
    return "\n".join(head) + "\n" + body + "\n"


def thread(*messages: str) -> bytes:
    return gzip.compress("".join(messages).encode("utf-8"))


class ImporterHarness(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def run_import(self, payload: bytes, **overrides) -> tuple[int, dict]:
        gz = self.tmp / "t.mbox.gz"
        gz.write_bytes(payload)
        ledger = self.tmp / "ledger.json"
        argv = [
            "--msgid",
            overrides.pop("msgid", "root@example.com"),
            "--alias",
            overrides.pop("alias", "T1"),
            "--slug",
            overrides.pop("slug", "fixture"),
            "--ordinal-start",
            str(overrides.pop("ordinal_start", 10)),
            "--thread-file",
            str(gz),
            "--no-network",
            "--lane-dir",
            str(self.tmp / "lane"),
            "--canonical-dir",
            str(self.tmp / "canonical"),
            "--ledger",
            str(ledger),
        ]
        for key, value in overrides.items():
            argv += [f"--{key.replace('_', '-')}", str(value)]
        code = lore.main(argv)
        return code, json.loads(ledger.read_text(encoding="utf-8"))

    def assertRejected(self, payload: bytes, error_class: str, **overrides) -> dict:
        code, verdict = self.run_import(payload, **overrides)
        self.assertEqual(code, 1)
        self.assertEqual(verdict["disposition"], "OUT")
        self.assertEqual(verdict["error_class"], error_class)
        self.assertFalse(sorted((self.tmp / "lane").glob("*.patch")))
        return verdict


class TestAcceptedThreads(ImporterHarness):
    def test_single_patch_thread(self) -> None:
        payload = thread(
            message("root@example.com", "[PATCH v3] subsystem: do the thing", DIFF)
        )
        code, ledger = self.run_import(payload)
        self.assertEqual(code, 0)
        self.assertEqual(ledger["revision"], "v3")
        self.assertEqual(len(ledger["patches"]), 1)
        self.assertEqual(ledger["patches"][0]["filename"], "0010-fixture.patch")
        self.assertEqual(
            (self.tmp / "lane" / "0010-fixture.patch").read_text(encoding="utf-8"), DIFF
        )

    def test_cover_letter_is_dropped_and_two_patches_are_ordered(self) -> None:
        payload = thread(
            message("cover@example.com", "[PATCH v2 0/2] a series", "no diff here"),
            message("two@example.com", "[PATCH v2 2/2] second", OTHER_DIFF),
            message("one@example.com", "[PATCH v2 1/2] first", DIFF),
        )
        code, ledger = self.run_import(payload)
        self.assertEqual(code, 0)
        self.assertEqual([p["sequence"] for p in ledger["patches"]], [1, 2])
        self.assertEqual(
            [p["filename"] for p in ledger["patches"]],
            ["0010-fixture-1.patch", "0011-fixture-2.patch"],
        )
        self.assertNotIn(
            "cover@example.com", [p["lore_msgid"] for p in ledger["patches"]]
        )

    def test_identical_duplicate_replies_collapse(self) -> None:
        posting = message("root@example.com", "[PATCH v1] one", DIFF)
        reply = message("reply@example.com", "Re: [PATCH v1] one", "looks fine")
        code, ledger = self.run_import(thread(posting, reply, posting, reply, posting))
        self.assertEqual(code, 0)
        self.assertEqual(len(ledger["patches"]), 1)

    def test_mboxrd_from_quoting_is_unescaped(self) -> None:
        quoted = DIFF + "\n>From the mailing list perspective this is escaped\n"
        code, ledger = self.run_import(
            thread(message("root@example.com", "[PATCH v1] one", quoted))
        )
        self.assertEqual(code, 0)
        mail = (self.tmp / "canonical" / "T1" / "01.mbox").read_text(encoding="utf-8")
        self.assertIn("\nFrom the mailing list perspective", mail)
        self.assertNotIn("\n>From the mailing list", mail)

    def test_two_imports_of_one_thread_are_byte_identical(self) -> None:
        payload = thread(
            message("root@example.com", "[PATCH v1] deterministic", DIFF)
        )
        code, first = self.run_import(payload)
        self.assertEqual(code, 0)
        source = (self.tmp / "lane" / "0010-fixture.patch").read_bytes()
        mail = (self.tmp / "canonical" / "T1" / "01.mbox").read_bytes()
        code, second = self.run_import(payload)
        self.assertEqual(code, 0)
        self.assertEqual(first, second)
        self.assertEqual(source, (self.tmp / "lane" / "0010-fixture.patch").read_bytes())
        self.assertEqual(mail, (self.tmp / "canonical" / "T1" / "01.mbox").read_bytes())


class TestRejectedThreads(ImporterHarness):
    def test_conflicting_duplicate_message_id(self) -> None:
        self.assertRejected(
            thread(
                message("root@example.com", "[PATCH v1] one", DIFF),
                message("root@example.com", "[PATCH v1] one", OTHER_DIFF),
            ),
            "duplicate-msgid-divergent-bytes",
        )

    def test_duplicate_diff_under_distinct_message_ids(self) -> None:
        verdict = self.assertRejected(
            thread(
                message("a@example.com", "[PATCH v1 1/2] one", DIFF),
                message("b@example.com", "[PATCH v1 2/2] two", DIFF),
            ),
            "duplicate-diff-distinct-msgid",
        )
        self.assertIn("a@example.com", verdict["error_detail"])
        self.assertIn("b@example.com", verdict["error_detail"])

    def test_reroll_contamination(self) -> None:
        self.assertRejected(
            thread(
                message("v1@example.com", "[PATCH v1] one", DIFF),
                message("v2@example.com", "[PATCH v2] one", OTHER_DIFF),
            ),
            "mixed-revision-thread",
        )

    def test_expected_revision_mismatch(self) -> None:
        self.assertRejected(
            thread(message("root@example.com", "[PATCH v2] one", DIFF)),
            "mixed-revision-thread",
            expect_revision="v3",
        )

    def test_missing_message_id(self) -> None:
        self.assertRejected(
            thread(
                message("root@example.com", "[PATCH v1] one", DIFF, with_msgid=False)
            ),
            "missing-message-id",
        )

    def test_missing_sequence_number(self) -> None:
        self.assertRejected(
            thread(
                message("a@example.com", "[PATCH v1 1/3] one", DIFF),
                message("b@example.com", "[PATCH v1 3/3] three", OTHER_DIFF),
            ),
            "missing-sequence",
        )

    def test_duplicate_sequence_number(self) -> None:
        self.assertRejected(
            thread(
                message("a@example.com", "[PATCH v1 1/2] one", DIFF),
                message("b@example.com", "[PATCH v1 1/2] one again", OTHER_DIFF),
            ),
            "duplicate-sequence",
        )

    def test_no_diff_bearing_message(self) -> None:
        self.assertRejected(
            thread(message("root@example.com", "[PATCH v1] one", "prose only")),
            "no-diff-bearing-message",
        )

    def test_wrong_compressed_digest(self) -> None:
        self.assertRejected(
            thread(message("root@example.com", "[PATCH v1] one", DIFF)),
            "digest-mismatch",
            expect_compressed_sha256="0" * 64,
        )

    def test_wrong_decompressed_digest(self) -> None:
        self.assertRejected(
            thread(message("root@example.com", "[PATCH v1] one", DIFF)),
            "digest-mismatch",
            expect_mbox_sha256="1" * 64,
        )

    def test_not_a_gzip_stream(self) -> None:
        self.assertRejected(b"plain text, not gzip", "unfetchable-canonical-thread")


class TestBoundedDecompression(unittest.TestCase):
    def test_ceiling_is_enforced(self) -> None:
        payload = gzip.compress(b"A" * (1024 * 1024))
        with self.assertRaises(lore.LoreImportError) as caught:
            lore.decompress_bounded(payload, max_bytes=4096)
        self.assertEqual(caught.exception.error_class, "decompression-limit-exceeded")

    def test_under_the_ceiling_is_returned_whole(self) -> None:
        payload = gzip.compress(b"B" * 5000)
        self.assertEqual(len(lore.decompress_bounded(payload, max_bytes=8192)), 5000)

    def test_message_count_ceiling(self) -> None:
        body = b"".join(
            f"From nobody {DATE}\nMessage-ID: <m{i}@example.com>\n\nbody\n".encode()
            for i in range(lore.MAX_MESSAGE_COUNT + 5)
        )
        with self.assertRaises(lore.LoreImportError) as caught:
            lore.split_thread(body)
        self.assertEqual(caught.exception.error_class, "decompression-limit-exceeded")


class TestUnfetchableCanonicalArchive(unittest.TestCase):
    """The one case where the discovery fallbacks are allowed to speak at all."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self._real_get = lore.http_get

        def fake_get(url: str) -> bytes:
            if url.endswith("t.mbox.gz"):
                raise lore.LoreImportError(
                    "unfetchable-canonical-thread", f"{url} returned 503"
                )
            return b"discovery endpoint says this Message-ID exists"

        lore.http_get = fake_get
        self.addCleanup(setattr, lore, "http_get", self._real_get)

    def test_discovery_succeeds_and_the_candidate_still_goes_out(self) -> None:
        ledger = self.tmp / "out.json"
        code = lore.main(
            [
                "--msgid",
                "blocked@example.com",
                "--alias",
                "T9",
                "--slug",
                "blocked",
                "--lane-dir",
                str(self.tmp / "lane"),
                "--canonical-dir",
                str(self.tmp / "canonical"),
                "--ledger",
                str(ledger),
            ]
        )
        verdict = json.loads(ledger.read_text(encoding="utf-8"))
        self.assertEqual(code, 1)
        self.assertEqual(verdict["disposition"], "OUT")
        self.assertEqual(verdict["error_class"], "unfetchable-canonical-thread")
        self.assertTrue(
            all("resolved" in value for value in verdict["diagnostics"].values()),
            verdict["diagnostics"],
        )
        self.assertNotIn("thread_compressed_sha256", verdict)
        self.assertNotIn("patches", verdict)
        self.assertFalse((self.tmp / "lane").exists())


if __name__ == "__main__":
    unittest.main()
