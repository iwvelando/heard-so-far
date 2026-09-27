"""The speech model is fetched and loaded only at its pinned revision."""

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import download_model
import model


def fake_hub(return_value="/cache/snapshot"):
    hub = types.ModuleType("huggingface_hub")
    hub.snapshot_download = MagicMock(return_value=return_value)
    return hub


class ModelTests(unittest.TestCase):
    def test_download_requests_pinned_revision(self):
        hub = fake_hub()
        with (
            patch.dict(sys.modules, {"huggingface_hub": hub}),
            patch.dict(download_model.os.environ, {}, clear=True),
            patch("builtins.print"),
        ):
            download_model.main()
        hub.snapshot_download.assert_called_once_with(model.MODEL, revision=model.REVISION)

    def test_reading_loads_pinned_local_snapshot(self):
        hub = fake_hub("/cache/pinned")
        with patch.dict(sys.modules, {"huggingface_hub": hub}):
            self.assertEqual(model.local_path(), "/cache/pinned")
        hub.snapshot_download.assert_called_once_with(model.MODEL, revision=model.REVISION)

    def test_missing_snapshot_points_to_setup(self):
        hub = fake_hub()
        hub.snapshot_download.side_effect = FileNotFoundError("not cached")
        with patch.dict(sys.modules, {"huggingface_hub": hub}):
            with self.assertRaisesRegex(SystemExit, "make download-model"):
                model.local_path()

    def test_snapshot_directory_is_the_pinned_revision(self):
        root = Path("/project")
        self.assertEqual(model.snapshot_dir(root).name, model.REVISION)
        self.assertTrue(str(model.snapshot_dir(root)).startswith("/project/.cache/huggingface/hub/"))


if __name__ == "__main__":
    unittest.main()
