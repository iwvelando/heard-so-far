"""Incomplete or mismatched extraction must not be accepted as evidence."""
import json
from pathlib import Path
import tempfile
import unittest

from transcript_io import validate_chunk, validate_run, windows


class TranscriptTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {"section_start": 5, "section_end": 1300,
                         "core_seconds": 600, "context_seconds": 20}

    def test_context_never_crosses_section_limits(self):
        spans = list(windows(self.manifest))
        self.assertEqual(spans[0]["clip_start"], 5)
        self.assertEqual(spans[-1]["clip_end"], 1300)
        self.assertEqual(spans[0]["core_end"], spans[1]["core_start"])
        self.assertEqual(spans[1]["clip_start"], spans[1]["core_start"] - 20)

    def test_reuse_refuses_mismatched_chunk_before_processing_words(self):
        expected = next(windows(self.manifest))
        chunk = expected | {"result": {"segments": []}}
        chunk["clip_end"] += 100
        with self.assertRaisesRegex(ValueError, "timestamps"):
            validate_chunk(chunk, expected)

    def test_missing_middle_chunk_and_unfinished_outputs_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            for index, span in enumerate(windows(self.manifest)):
                (folder / f"chunk_{index:03}.json").write_text(json.dumps(span | {"result": {"segments": []}}))
            with self.assertRaisesRegex(ValueError, "final outputs"):
                validate_run(folder, self.manifest)
            (folder / "transcript.txt").write_text("Synthetic text")
            (folder / "boundaries.json").write_text("[]")
            validate_run(folder, self.manifest)
            (folder / "chunk_001.json").unlink()
            with self.assertRaisesRegex(ValueError, "required chunk"):
                validate_run(folder, self.manifest)

    def test_nonfinite_or_zero_chunk_size_rejected(self):
        for value in (0, -1, float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                list(windows(self.manifest | {"core_seconds": value}))


if __name__ == "__main__":
    unittest.main()
