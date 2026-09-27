"""The public-file check must catch private material even if Git tracks it."""

import tempfile
import unittest
from pathlib import Path

from check_public import check_paths


class PublicTests(unittest.TestCase):
    def test_private_files_and_unreviewed_outputs_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            names = [
                "companion/journal/book/entry.json",
                "companion/progress.json",
                "audiobooks/book.m4b",
                ".env",
                "answer.md",
                "CLAUDE.local.md",
            ]
            self.assertEqual(len(check_paths(names, root)), len(names))
            self.assertEqual(check_paths(["AGENTS.md", "CLAUDE.md"], root), [])

    def test_public_symlink_cannot_point_at_private_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").symlink_to(root / "private-book.txt")
            self.assertIn("symlinks", check_paths(["README.md"], root)[0])


if __name__ == "__main__":
    unittest.main()
