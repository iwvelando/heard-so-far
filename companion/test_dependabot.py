"""Dependabot auto-merge accepts only updates that change no major version."""
import os
from pathlib import Path
import subprocess
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / ".github/scripts/dependabot-safe-update.sh"


def safe(body, commit_message=""):
    env = dict(os.environ, COMMIT_MESSAGE=commit_message)
    result = subprocess.run(["bash", str(SCRIPT)], input=body, text=True, capture_output=True, env=env)
    return result.returncode == 0


class SafeUpdateTests(unittest.TestCase):
    def test_minor_and_patch_updates_are_safe(self):
        self.assertTrue(safe("Bumps [actions/checkout](https://example.test) from 7.0.1 to 7.0.2.\n"))
        self.assertTrue(safe("Bumps the actions-minor-and-patch group with 1 update:\n"
                             "Updates `actions/setup-python` from 7.0.0 to 7.1.0\n"))

    def test_major_update_is_not_safe(self):
        self.assertFalse(safe("Bumps [actions/checkout](https://example.test) from 7.0.1 to 8.0.0.\n"))

    def test_one_major_in_a_group_blocks_the_group(self):
        self.assertFalse(safe("Updates `actions/checkout` from 7.0.1 to 7.0.2\n"
                              "Updates `actions/setup-python` from v7.0.0 to v8.0.0\n"))

    def test_release_notes_alone_are_not_read_as_updates(self):
        self.assertFalse(safe("Release notes\n> Upgrade from 1.0.0 to 1.0.1 is recommended.\n"))

    def test_commit_metadata_can_mark_a_major(self):
        self.assertFalse(safe("Bumps [example](https://example.test) from 7.0.1 to 7.0.2.\n",
                              "update-type: version-update:semver-major"))


if __name__ == "__main__":
    unittest.main()
