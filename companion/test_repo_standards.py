"""Repository conventions shared with the project's sibling repositories."""

import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCKS = ["companion/requirements.txt", "companion/requirements-dev.txt"]


def requirements(path):
    """Return (pin, hashes) per requirement, joining backslash continuations."""
    text = (ROOT / path).read_text().replace("\\\n", " ")
    entries = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            entries.append((line.split()[0], re.findall(r"--hash=sha256:[0-9a-f]{64}", line)))
    return entries


class LockTests(unittest.TestCase):
    def test_every_installed_package_is_pinned_with_hashes(self):
        for path in LOCKS:
            entries = requirements(path)
            self.assertTrue(entries, path)
            for pin, hashes in entries:
                self.assertRegex(pin, r"^[A-Za-z0-9._-]+(\[[^]]+\])?==[^=;]+$", f"{path}: {pin}")
                self.assertTrue(hashes, f"{path}: {pin} has no hash")

    def test_locks_are_compiled_from_their_inputs(self):
        for path in LOCKS:
            source = path.replace(".txt", ".in")
            self.assertTrue((ROOT / source).is_file(), source)
            self.assertIn("make lock", (ROOT / path).read_text().split("\n", 3)[1], path)
            locked = {pin for pin, _ in requirements(path)}
            for line in (ROOT / source).read_text().splitlines():
                line = line.split("#", 1)[0].strip()
                if line:
                    self.assertIn(line, locked, f"{source}: {line} is not locked in {path}")


class FileConventionTests(unittest.TestCase):
    def test_editor_and_line_ending_settings_exist(self):
        self.assertIn("root = true", (ROOT / ".editorconfig").read_text())
        self.assertIn("* text=auto eol=lf", (ROOT / ".gitattributes").read_text())

    def test_local_tool_state_is_ignored(self):
        paths = [
            ".claude/scheduled_tasks.lock",
            ".claude/settings.local.json",
            "debug.log",
            ".vscode/settings.json",
            ".idea/workspace.xml",
            "notes.md.swp",
            "notes.md~",
            ".ruff_cache/CACHEDIR.TAG",
        ]
        result = subprocess.run(
            ["git", "-c", "core.excludesFile=/dev/null", "check-ignore", "--no-index", *paths],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(sorted(result.stdout.split()), sorted(paths))

    def test_check_includes_formatting_and_lint(self):
        makefile = (ROOT / "Makefile").read_text()
        check = re.search(r"^check:(.*)$", makefile, re.M).group(1).split()
        self.assertIn("lint", check)
        self.assertTrue((ROOT / "ruff.toml").is_file())


if __name__ == "__main__":
    unittest.main()
