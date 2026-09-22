"""Progress matching and extraction boundary regression tests; no ASR required."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import position
import transcribe_section


def chapter(title, start, end):
    return {"start_time": str(start), "end_time": str(end), "tags": {"title": title}}


class PositionTests(unittest.TestCase):
    def setUp(self):
        self.chapters = [chapter("Opening", 0, 80), chapter("Repeated chapter", 80, 680),
                         chapter("Repeated chapter", 680, 1580.25),
                         chapter("UNREAD TITLE", 1580.25, 2000)]
        self.p = position.match(self.chapters, "Repeated", 480, 420, audio_file="audiobooks/example.m4b")

    def test_duplicate_title_resolved_by_duration(self):
        self.assertEqual(self.p["track_index_1_based"], 3)
        self.assertEqual(self.p["title_occurrence_1_based"], 2)
        self.assertAlmostEqual(position.validate(self.p, self.chapters), 1155)

    def test_ambiguous_duration_requires_identifier(self):
        self.chapters.append(chapter("Repeated chapter", 2000, 2900.25))
        with self.assertRaisesRegex(ValueError, "found 2"):
            position.match(self.chapters, "Repeated", 480, 420, audio_file="audiobooks/example.m4b")
        self.assertEqual(position.match(self.chapters, "Repeated", 480, 420, 3,
                                       audio_file="audiobooks/example.m4b")["track_index_1_based"], 3)

    def test_future_titles_not_shown(self):
        rows = position.visible_tracks(self.chapters, self.p["cutoff_audio_seconds"])
        self.assertNotIn("UNREAD TITLE", json.dumps(rows))
        self.assertEqual(len(rows), 3)

    def test_corrupted_progress_rejected(self):
        for key, value in [("cutoff_audio_seconds", 999999), ("reported_remaining_seconds", -1),
                           ("boundary_buffer_seconds", 0), ("embedded_track_start_seconds", 0),
                           ("embedded_track_end_seconds", float("nan")), ("track_title", "wrong")]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                position.validate(self.p | {key: value}, self.chapters)

    def test_rounding_at_track_end(self):
        cs = [chapter("Rounded", 0, 100.6)]
        p = position.match(cs, "Rounded", 101, 0, audio_file="audiobooks/example.m4b")
        self.assertAlmostEqual(p["cutoff_audio_seconds"], 100.6)
        self.assertAlmostEqual(position.validate(p, cs), 95.6)

    def test_time_validation(self):
        self.assertEqual(position.seconds("12:34"), 754)
        self.assertEqual(position.seconds("1:02:03"), 3723)
        for t in ["42:99", "-1:00", "nan", "1:60:00", "00:00:00:00"]:
            with self.subTest(time=t), self.assertRaises(ValueError):
                position.seconds(t)

    def test_explicit_source_required_without_saved_state(self):
        with self.assertRaisesRegex(ValueError, "requires --audio"):
            position.resolve_audio(None, None)

    def test_saved_and_replacement_sources(self):
        saved = {"audio_file": "audiobooks/first.m4b"}
        self.assertEqual(position.resolve_audio(None, saved), "audiobooks/first.m4b")
        self.assertEqual(position.resolve_audio("audiobooks/second.m4b", saved), "audiobooks/second.m4b")

    def test_non_ascii_titles(self):
        cs = [chapter("第１章：出発", 0, 100)]
        p = position.match(cs, "第1章", 60, 40, audio_file="audiobooks/example.m4b")
        self.assertEqual(p["track_index_1_based"], 1)
        self.assertEqual(position.normalize("ÉTÉ"), position.normalize("été"))

    def test_language_retained_only_for_same_source(self):
        with tempfile.TemporaryDirectory() as directory:
            progress_path = Path(directory) / "progress.json"
            cs = [chapter("Example", 0, 100)]
            initial = position.match(cs, "Example", 60, 40, audio_file="audiobooks/first.m4b")
            initial["language"] = "es"
            progress_path.write_text(json.dumps(initial))
            with patch.object(position, "PROGRESS", progress_path), patch.object(position, "probe", return_value=cs), \
                 patch("builtins.print"):
                argv = ["position", "set", "--title", "Example", "--elapsed", "01:00", "--remaining", "00:40"]
                with patch.object(sys, "argv", argv):
                    position.main()
                self.assertEqual(json.loads(progress_path.read_text())["language"], "es")
                with patch.object(sys, "argv", argv + ["--audio", "audiobooks/second.m4b"]):
                    position.main()
                p = json.loads(progress_path.read_text())
                self.assertEqual(p["audio_file"], "audiobooks/second.m4b")
                self.assertIsNone(p["language"])


class StopBeforeASR(Exception):
    pass


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.chapters = [chapter("Completed", 0, 100), chapter("Current", 100, 300)]
        self.p = position.match(self.chapters, "Current", 150, 50, audio_file="audiobooks/example.m4b")

    def run_until_manifest(self, extra):
        probe = type("Probe", (), {"stdout": json.dumps({"chapters": self.chapters})})()
        written = []
        def capture(path, text):
            written.append((path, text))
            raise StopBeforeASR()
        argv = ["transcribe_section", "--first-track", "2", "--last-track", "2", *extra]
        with patch.object(sys, "argv", argv), patch.object(Path, "read_text", return_value=json.dumps(self.p)), \
             patch.object(transcribe_section.subprocess, "run", return_value=probe), \
             patch.object(Path, "mkdir"), patch.object(Path, "exists", return_value=False), \
             patch.object(Path, "write_text", autospec=True, side_effect=capture), \
             patch.object(Path, "stat", return_value=type("Stat", (), {"st_size": 100, "st_mtime_ns": 1})()):
            try:
                transcribe_section.main()
            except StopBeforeASR:
                return written[0]

    def test_unfinished_whole_track_fails(self):
        with self.assertRaisesRegex(ValueError, "not been completely heard"):
            self.run_until_manifest([])

    def test_partial_request_stops_before_progress(self):
        path, text = self.run_until_manifest(["--through", "02:30"])
        self.assertEqual(json.loads(text)["section_end"], 245)
        self.assertTrue(path.parent.name.startswith("query_"))

    def test_requested_end_is_not_advanced(self):
        _, text = self.run_until_manifest(["--through", "01:00"])
        self.assertEqual(json.loads(text)["section_end"], 160)

    def test_future_partial_request_fails(self):
        with self.assertRaisesRegex(ValueError, "not been heard"):
            self.run_until_manifest(["--through", "02:40"])

    def test_each_default_output_is_fresh(self):
        a, _ = self.run_until_manifest(["--through", "01:00"])
        b, _ = self.run_until_manifest(["--through", "01:00"])
        self.assertNotEqual(a, b)


if __name__ == "__main__":
    unittest.main()
