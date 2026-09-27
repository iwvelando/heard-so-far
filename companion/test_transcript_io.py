"""Incomplete or mismatched extraction must not be accepted as evidence."""

import json
import tempfile
import unittest
from pathlib import Path

from transcript_io import coverage_gaps, local_label, repeated_runs, validate_chunk, validate_run, windows


class TranscriptTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {"section_start": 5, "section_end": 1300, "core_seconds": 600, "context_seconds": 20}

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

    def test_windows_restart_at_track_breaks_and_context_stays_inside_track(self):
        manifest = self.manifest | {
            "tracks": [{"track": 3, "start": 0, "end": 700}, {"track": 4, "start": 700, "end": 1400}]
        }
        spans = list(windows(manifest))
        self.assertEqual([(s["core_start"], s["core_end"]) for s in spans], [(5, 605), (605, 700), (700, 1300)])
        self.assertEqual((spans[1]["clip_start"], spans[1]["clip_end"]), (585, 700))
        self.assertEqual(spans[2]["clip_start"], 700)

    def test_manifest_without_tracks_keeps_continuous_windows(self):
        self.assertEqual([s["core_start"] for s in windows(self.manifest)], [5, 605, 1205])

    def test_nonfinite_track_start_rejected(self):
        manifest = self.manifest | {"tracks": [{"track": 1, "start": float("nan"), "end": 9}]}
        with self.assertRaises(ValueError):
            list(windows(manifest))

    def test_coverage_gaps_report_silent_stretches_including_edges(self):
        words = [(10, 11), (12, 13), (40, 41), (42, 43)]
        self.assertEqual(
            coverage_gaps(words, 5, 70, threshold=15),
            [{"start": 13, "end": 40, "seconds": 27}, {"start": 43, "end": 70, "seconds": 27}],
        )
        self.assertEqual(coverage_gaps([], 0, 10, threshold=15), [])
        self.assertEqual(coverage_gaps([], 0, 30, threshold=15), [{"start": 0, "end": 30, "seconds": 30}])

    def test_repeated_runs_flag_consecutive_identical_lines_only(self):
        lines = [
            (0, 1, "Real sentence."),
            (1, 2, "Loop."),
            (2, 3, " loop"),
            (3, 4, "Loop."),
            (4, 5, "Another."),
            (5, 6, "Twice."),
            (6, 7, "Twice."),
        ]
        self.assertEqual(repeated_runs(lines, minimum=3), [{"start": 1, "end": 4, "count": 3}])

    def test_local_label_uses_containing_track(self):
        tracks = [{"track": 14, "start": 100, "end": 4470}, {"track": 15, "start": 4470, "end": 6744}]
        self.assertEqual(local_label(4470 + 2160.4, tracks), "track 15 36:00")
        self.assertEqual(local_label(100 + 3725, tracks), "track 14 1:02:05")
        self.assertIsNone(local_label(50, tracks))

    def test_track_aware_run_requires_quality_report(self):
        manifest = self.manifest | {"tracks": [{"track": 1, "start": 0, "end": 1400}]}
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            for index, span in enumerate(windows(manifest)):
                (folder / f"chunk_{index:03}.json").write_text(json.dumps(span | {"result": {"segments": []}}))
            (folder / "transcript.txt").write_text("Synthetic text")
            (folder / "boundaries.json").write_text("[]")
            with self.assertRaisesRegex(ValueError, "final outputs"):
                validate_run(folder, manifest)
            (folder / "quality.json").write_text("{}")
            validate_run(folder, manifest)


if __name__ == "__main__":
    unittest.main()
