"""Verify cleanup is restricted to derived data and arguments remain literal."""
from pathlib import Path
from contextlib import redirect_stdout
import io
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tasks
import locking


class HelpersTests(unittest.TestCase):
    def test_cleanup_preserves_source_and_progress(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            transcript = root / "companion/transcripts/run"
            transcript.mkdir(parents=True)
            (transcript / "text.txt").write_text("derived")
            audio = root / "purchased.m4b"
            audio.write_bytes(b"source")
            progress = root / "companion/progress.json"
            progress.write_text("personal state")
            journal = root / "companion/journal/book/entry.json"
            journal.parent.mkdir(parents=True)
            journal.write_text("private journal")
            with patch.object(tasks, "ROOT", root), patch.object(locking, "ROOT", root), \
                 patch.object(sys, "argv", ["tasks", "clean-transcripts"]), redirect_stdout(io.StringIO()):
                tasks.main()
            self.assertFalse(transcript.parent.exists())
            self.assertEqual(audio.read_bytes(), b"source")
            self.assertEqual(progress.read_text(), "personal state")
            self.assertEqual(journal.read_text(), "private journal")

    def test_cleanup_refuses_symlinked_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            original = root / "source"
            original.mkdir()
            alias = root / "transcripts"
            alias.symlink_to(original, target_is_directory=True)
            with self.assertRaisesRegex(SystemExit, "symlinked"):
                tasks.clean(alias)
            self.assertTrue(original.exists())

    def test_cleanup_refuses_while_transcription_locked(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            with patch.object(locking, "ROOT", root), locking.exclusive():
                with self.assertRaisesRegex(SystemExit, "active"), locking.exclusive():
                    self.fail("Lock was not exclusive")

    def test_titles_are_passed_as_literal_arguments(self):
        title = 'A "quoted" title with apostrophe\' and $()'
        with patch.dict(tasks.os.environ, {"TITLE": title, "ELAPSED": "01:00", "REMAINING": "02:00"}, clear=True), \
             patch.object(sys, "argv", ["tasks", "progress"]), patch.object(tasks.subprocess, "run") as run:
            tasks.main()
        command = run.call_args.args[0]
        self.assertEqual(command[command.index("--title") + 1], title)
        self.assertNotIn("shell", run.call_args.kwargs)


if __name__ == "__main__":
    unittest.main()
