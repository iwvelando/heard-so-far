"""User-correction format and boundary tests using synthetic data only."""

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corrections


def chapter(title, start, end):
    return {"start_time": str(start), "end_time": str(end), "tags": {"title": title}}


AUDIO = "audiobooks/example.m4b"
CHAPTERS = [chapter("Opening", 0, 300), chapter("Second part", 300, 900), chapter("UNREAD TITLE", 900, 1200)]
CUTOFF = 800


def entry(**changes):
    return {
        "track": 2,
        "track_title": "Second part",
        "start": "03:59",
        "end": "04:14",
        "asr": "synthetic misheard words",
        "corrected": "synthetic corrected words",
        "attribution": "user",
    } | changes


def problems(data):
    return corrections.check_file(data, CHAPTERS, AUDIO, CUTOFF)


class CheckFileTests(unittest.TestCase):
    def test_valid_file_passes(self):
        self.assertEqual(problems({"source_audio": AUDIO, "corrections": [entry(), entry(note="optional")]}), [])
        self.assertEqual(problems({"source_audio": AUDIO, "corrections": []}), [])

    def test_source_is_required_and_must_match(self):
        self.assertTrue(problems({"corrections": [entry()]}))
        self.assertTrue(problems({"source_audio": "audiobooks/other.m4b", "corrections": [entry()]}))

    def test_unlocated_or_unscoped_entries_rejected(self):
        without_track = entry()
        del without_track["track"]
        timing_only = {k: v for k, v in entry().items() if k not in ("track", "track_title", "start", "end")}
        for name, bad in [
            ("free-text timing", entry(timing="Not yet located precisely")),
            ("missing track", without_track),
            ("timing instead of an interval", timing_only | {"timing": "near track 03:59"}),
        ]:
            with self.subTest(name):
                self.assertTrue(problems({"source_audio": AUDIO, "corrections": [bad]}))

    def test_dangling_top_level_reference_rejected(self):
        data = {"source_audio": AUDIO, "transcript": "companion/transcripts/pilot.json", "corrections": []}
        self.assertTrue(problems(data))

    def test_invalid_fields_rejected(self):
        for name, bad in [
            ("blank asr", entry(asr=" ")),
            ("blank correction", entry(corrected="")),
            ("missing attribution", entry(attribution="")),
            ("track zero", entry(track=0)),
            ("track out of range", entry(track=9)),
            ("boolean track", entry(track=True)),
            ("title mismatch", entry(track_title="Opening")),
            ("reversed interval", entry(start="04:14", end="03:59")),
            ("bad clock", entry(start="3 minutes")),
            ("past track end", entry(start="09:00", end="10:30")),
            ("past listening limit", entry(start="07:50", end="08:30")),
        ]:
            with self.subTest(name):
                self.assertTrue(problems({"source_audio": AUDIO, "corrections": [bad]}))

    def test_corrections_must_be_a_list(self):
        self.assertTrue(problems({"source_audio": AUDIO, "corrections": {}}))
        self.assertTrue(problems([]))


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "user_corrections.json"
        for target, value in [
            ("CORRECTIONS", self.path),
            ("context", lambda: (AUDIO, CHAPTERS, CUTOFF)),
        ]:
            patcher = patch.object(corrections, target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def run_command(self, *args, stdin=""):
        out = io.StringIO()
        with patch.object(sys, "argv", ["corrections", *args]), patch.object(sys, "stdin", io.StringIO(stdin)):
            with patch.object(sys, "stdout", out):
                corrections.main()
        return out.getvalue()

    def test_missing_file_is_empty_and_valid(self):
        self.assertIn("OK: 0 corrections", self.run_command("check"))

    def test_add_creates_file_and_preserves_existing_entries(self):
        self.run_command("add", stdin=json.dumps(entry()))
        self.run_command("add", stdin=json.dumps(entry(start="02:00", end="02:05")))
        data = json.loads(self.path.read_text())
        self.assertEqual(data["source_audio"], AUDIO)
        self.assertEqual([c["start"] for c in data["corrections"]], ["03:59", "02:00"])

    def test_add_rejects_invalid_entry_without_writing(self):
        self.run_command("add", stdin=json.dumps(entry()))
        before = self.path.read_text()
        for bad in [entry(timing="unknown"), entry(start="07:50", end="08:30")]:
            with self.subTest(bad=bad), self.assertRaises(SystemExit):
                self.run_command("add", stdin=json.dumps(bad))
        self.assertEqual(self.path.read_text(), before)

    def test_add_refuses_other_source(self):
        self.path.write_text(json.dumps({"source_audio": "audiobooks/other.m4b", "corrections": []}))
        with self.assertRaises(SystemExit):
            self.run_command("add", stdin=json.dumps(entry()))

    def test_check_reports_without_book_text(self):
        self.path.write_text(json.dumps({"source_audio": AUDIO, "corrections": [entry(track=3, track_title="x")]}))
        out = io.StringIO()
        with patch.object(sys, "stderr", out), self.assertRaises(SystemExit) as raised:
            self.run_command("check")
        message = str(raised.exception.code) + out.getvalue()
        self.assertIn("correction 1", message)
        for secret in ("synthetic", "UNREAD TITLE", "Second part"):
            self.assertNotIn(secret, message)


if __name__ == "__main__":
    unittest.main()
