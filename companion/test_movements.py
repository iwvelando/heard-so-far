"""Synthetic producer/consumer conformance and private export safeguards."""

import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import movements

FIXTURE = json.loads((movements.ROOT / "spec/movement-format-cases.json").read_text())


class FormatTests(unittest.TestCase):
    def test_shared_conformance_cases(self):
        for case in FIXTURE["cases"]:
            source = FIXTURE["source"]
            if "replace" in case:
                source = source.replace(*case["replace"], 1)
            source += case.get("append", "")
            meta = {**FIXTURE["metadata"], **case.get("metadata_patch", {})}
            if case.get("rehash", True):
                meta["movements_sha256"] = hashlib.sha256(source.encode()).hexdigest()
            with self.subTest(case=case["name"]):
                if case["valid"]:
                    movements.validate_pair(source, meta)
                else:
                    with self.assertRaises(ValueError):
                        movements.validate_pair(source, meta)

    def test_unversioned_is_not_a_new_export(self):
        with self.assertRaises(ValueError):
            movements.validate_pair("legacy", {})


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.identity = {"resolved_audio_path": "synthetic-audio.m4b", "size": 100, "mtime_ns": 1000}
        progress = {
            "track_index_1_based": 1,
            "embedded_track_start_seconds": 0,
            "reported_elapsed_seconds": 60,
        }
        self.ctx = (progress, self.identity, 55)
        self.source = FIXTURE["source"]
        self.payload = {
            "movements": self.source,
            "query_interval": {"start": 0, "end": 50},
            "reading_endpoint": {"chapter": 1, "coverage": "partial"},
            "manifests": ["run/manifest.json"],
        }
        run = self.root / "run"
        run.mkdir()
        self.manifest = {
            "source_audio": "synthetic-audio.m4b",
            "source_size": 100,
            "source_mtime_ns": 1000,
            "section_start": 0,
            "section_end": 50,
        }
        self.manifest_path = run / "manifest.json"
        self.manifest_path.write_text(json.dumps(self.manifest))

    def create(self, name="snapshot"):
        with patch.object(movements, "ROOT", self.root), patch.object(movements, "validate_run"):
            return movements.create(self.payload, self.ctx, name)

    def test_complete_pair_is_immutable_and_gate_precedes_body(self):
        folder = self.create()
        meta = json.loads((folder / "metadata.json").read_text())
        self.assertEqual(meta["movements_sha256"], hashlib.sha256(self.source.encode()).hexdigest())
        with self.assertRaises(ValueError):
            self.create()
        with patch.object(movements, "ROOT", self.root):
            movements.check(folder, self.ctx, 50)
            # Invalid scope is rejected before even attempting to open the body.
            (folder / "movements.md").unlink()
            with self.assertRaisesRegex(ValueError, "scope"):
                movements.check(folder, self.ctx, 40)

    def test_complete_run_is_checked_without_a_model(self):
        manifest = {**self.manifest, "core_seconds": 50, "context_seconds": 0}
        self.manifest_path.write_text(json.dumps(manifest))
        run = self.manifest_path.parent
        chunk = {"core_start": 0, "core_end": 50, "clip_start": 0, "clip_end": 50, "result": {"segments": []}}
        (run / "chunk_000.json").write_text(json.dumps(chunk))
        for name in ("transcript.txt", "boundaries.json"):
            (run / name).write_text("synthetic")
        with patch.object(movements, "ROOT", self.root):
            folder = movements.create(self.payload, self.ctx, "complete-run")
            movements.check(folder, self.ctx, 50)
            (run / "chunk_000.json").unlink()
            with self.assertRaises(ValueError):
                movements.create(self.payload, self.ctx, "missing-chunk")
        self.assertFalse((self.root / "companion/visualizations/missing-chunk").exists())

    def test_path_traversal_and_symlinked_body_are_rejected_before_reading(self):
        folder = self.create()
        with patch.object(movements, "ROOT", self.root):
            with self.assertRaisesRegex(ValueError, "inside"):
                movements.check(folder / ".." / ".." / ".." / "run", self.ctx, 50)
            body = folder / "movements.md"
            body.unlink()
            body.symlink_to(self.manifest_path)
            with self.assertRaisesRegex(ValueError, "symlink"):
                movements.check(folder, self.ctx, 50)

    def test_changed_source_and_partial_run_never_publish(self):
        for field, value in [("source_size", 101), ("section_end", 56)]:
            manifest = {**self.manifest, field: value}
            self.manifest_path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                self.create()
        self.manifest_path.write_text(json.dumps(self.manifest))
        with (
            patch.object(movements, "ROOT", self.root),
            patch.object(movements, "validate_run", side_effect=ValueError("incomplete")),
        ):
            with self.assertRaises(ValueError):
                movements.create(self.payload, self.ctx, "snapshot")
        self.assertFalse((self.root / "companion/visualizations/snapshot").exists())

    def test_reuse_checks_scope_identity_and_tampering(self):
        folder = self.create()
        with patch.object(movements, "ROOT", self.root):
            changed = (self.ctx[0], {**self.identity, "size": 101}, self.ctx[2])
            with self.assertRaisesRegex(ValueError, "source"):
                movements.check(folder, changed, 50)
            (folder / "movements.md").write_text(self.source + "Changed.\n")
            with self.assertRaisesRegex(ValueError, "hash"):
                movements.check(folder, self.ctx, 50)

    def test_unsafe_paths_and_bad_payload_leave_no_export(self):
        for name in ["../escape", "/absolute", ".pending", ""]:
            with self.assertRaises(ValueError):
                self.create(name)
        unsafe = self.root / "companion"
        unsafe.symlink_to(self.root / "run", target_is_directory=True)
        with self.assertRaises(ValueError):
            self.create()

    def test_unknown_payload_fields_and_invalid_ledger_are_rejected(self):
        self.payload["unexpected"] = "private"
        with self.assertRaises(ValueError):
            self.create()
        del self.payload["unexpected"]
        self.payload["movements"] = "invalid"
        with self.assertRaises(ValueError):
            self.create()

    def test_cli_diagnostic_does_not_include_private_payload(self):
        self.payload["unexpected"] = "SYNTHETIC-PRIVATE"
        stderr = io.StringIO()
        with (
            patch.object(movements, "ROOT", self.root),
            patch.object(movements, "context", return_value=self.ctx),
            patch("sys.argv", ["movements.py", "create", "--name", "snapshot"]),
            patch("sys.stdin", io.StringIO(json.dumps(self.payload))),
            patch("sys.stderr", stderr),
        ):
            with self.assertRaises(SystemExit) as failure:
                movements.main()
        self.assertEqual(failure.exception.code, 1)
        self.assertIn("payload fields", stderr.getvalue())
        self.assertNotIn("SYNTHETIC-PRIVATE", stderr.getvalue())

    def test_requested_earlier_endpoint_cannot_reuse_later_evidence(self):
        self.payload["query_interval"] = {"start": 0, "end": 40}
        with self.assertRaises(ValueError):
            self.create()


if __name__ == "__main__":
    unittest.main()
