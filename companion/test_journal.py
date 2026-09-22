"""Journal isolation and boundary tests using synthetic local data only."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import journal


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        root_patch = patch.object(journal, "ROOT", self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        self.source = {"path": str(self.root / "book.m4b"), "size": 42, "mtime_ns": 100}
        self.ctx = ({"cutoff_audio_seconds": 105}, self.source, "a" * 64, 100)
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text(json.dumps({"source_audio": "book.m4b",
            "source_size": 42, "source_mtime_ns": 100,
            "section_start": 10, "section_end": 50, "core_seconds": 600, "context_seconds": 20}))
        (self.root / "chunk_000.json").write_text(json.dumps({"core_start": 10,
            "core_end": 50, "clip_start": 10, "clip_end": 50, "result": {"segments": []}}))
        (self.root / "transcript.txt").write_text("Synthetic evidence")
        (self.root / "boundaries.json").write_text("[]")
        self.payload = {"question": "What happened?", "answer": "A prepared answer.",
                        "scope": {"start": 10, "end": 50},
                        "manifests": [str(self.manifest)]}

    def test_record_retains_exact_text_and_evidence_after_transcript_deletion(self):
        metadata = journal.record(self.payload, self.ctx)
        self.manifest.unlink()
        body = journal.read_entry(self.ctx, 50, metadata["id"])
        self.assertEqual(body["question"], self.payload["question"])
        self.assertEqual(body["answer"], self.payload["answer"])
        self.assertEqual(body["status"], "prepared")
        self.assertEqual(body["evidence"][0]["manifest"]["section_end"], 50)
        rows = journal.entries(self.ctx, 50)
        self.assertEqual(len(rows), 1)
        self.assertNotIn("question", rows[0])
        self.assertNotIn("answer", rows[0])

    def test_later_entry_body_is_never_opened_for_earlier_query(self):
        metadata = journal.record(self.payload, self.ctx)
        body_path = self.root / "companion/journal" / self.ctx[2] / metadata["id"] / "entry.json"
        body_path.write_text("invalid JSON; must not be opened")
        self.assertEqual(journal.entries(self.ctx, 49), [])
        with self.assertRaisesRegex(ValueError, "outside"):
            journal.read_entry(self.ctx, 49, metadata["id"])

    def test_rewound_progress_and_different_book_exclude_entry(self):
        metadata = journal.record(self.payload, self.ctx)
        rewound = (*self.ctx[:3], 40)
        self.assertEqual(journal.entries(rewound, 100), [])
        with self.assertRaisesRegex(ValueError, "outside"):
            journal.read_entry(rewound, 100, metadata["id"])
        different = (self.ctx[0], self.source, "b" * 64, 100)
        self.assertEqual(journal.entries(different, 100), [])

    def test_wrong_or_changed_source_rejected(self):
        for field, value in (("source_audio", "other.m4b"), ("source_size", 43), ("source_mtime_ns", 101)):
            with self.subTest(field=field):
                original = self.manifest.read_text()
                manifest = json.loads(original)
                manifest[field] = value
                self.manifest.write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError, "source"):
                    journal.record(self.payload, self.ctx)
                self.manifest.write_text(original)

    def test_scope_and_all_consulted_evidence_must_fit(self):
        self.payload["scope"]["end"] = 101
        with self.assertRaisesRegex(ValueError, "listening limit"):
            journal.record(self.payload, self.ctx)
        self.payload["scope"]["end"] = 49
        with self.assertRaisesRegex(ValueError, "beyond"):
            journal.record(self.payload, self.ctx)
        self.assertFalse((self.root / "companion/journal").exists())

    def test_invalid_times_and_traversal_rejected(self):
        for value in (float("nan"), float("inf"), -1, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                journal.entries(self.ctx, value)
        with self.assertRaisesRegex(ValueError, "ID"):
            journal.read_entry(self.ctx, 100, "../other")

    def test_incomplete_transcript_cannot_be_recorded(self):
        (self.root / "chunk_000.json").unlink()
        with self.assertRaisesRegex(ValueError, "incomplete"):
            journal.record(self.payload, self.ctx)

    def test_stored_progress_never_exposes_later_titles(self):
        metadata = journal.record(self.payload, self.ctx)
        path = self.root / "companion/journal" / self.ctx[2] / metadata["id"] / "entry.json"
        body = json.loads(path.read_text())
        body["progress"]["track_title"] = "LATER CHAPTER TITLE"
        path.write_text(json.dumps(body))
        returned = journal.read_entry(self.ctx, 50, metadata["id"])
        self.assertNotIn("LATER CHAPTER TITLE", json.dumps(returned))
        self.assertNotIn("progress", returned)

    def test_archived_evidence_must_match_declared_limit(self):
        metadata = journal.record(self.payload, self.ctx)
        path = self.root / "companion/journal" / self.ctx[2] / metadata["id"] / "entry.json"
        body = json.loads(path.read_text())
        body["evidence"][0]["manifest"]["section_end"] = 70
        path.write_text(json.dumps(body))
        with self.assertRaisesRegex(ValueError, "declared time limit"):
            journal.read_entry(self.ctx, 50, metadata["id"])

    def test_partial_entries_and_bad_metadata_are_skipped(self):
        folder = self.root / "companion/journal" / self.ctx[2]
        pending = folder / ".pending-incomplete"
        pending.mkdir(parents=True)
        (pending / "meta.json").write_text("{}")
        broken = folder / ("c" * 32)
        broken.mkdir()
        (broken / "meta.json").write_text("{}")
        self.assertEqual(journal.entries(self.ctx, 100), [])


if __name__ == "__main__":
    unittest.main()
