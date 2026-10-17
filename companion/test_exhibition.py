"""Curated export boundaries and privacy with synthetic source material."""

import base64
import copy
import json
import struct
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

import exhibition


class ExhibitionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        root_patch = patch.object(exhibition, "ROOT", self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        source = {"path": str(self.root / "source.m4b"), "size": 12, "mtime_ns": 34}
        self.ctx = ({}, source, "synthetic", 100)
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text(
            json.dumps(
                {
                    "source_audio": "source.m4b",
                    "source_size": 12,
                    "source_mtime_ns": 34,
                    "section_start": 10,
                    "section_end": 90,
                    "core_seconds": 40,
                    "context_seconds": 0,
                }
            )
        )
        for i, (a, b) in enumerate([(10, 50), (50, 90)]):
            (self.root / f"chunk_{i:03}.json").write_text(
                json.dumps(
                    {
                        "core_start": a,
                        "core_end": b,
                        "clip_start": a,
                        "clip_end": b,
                        "result": {"segments": []},
                    }
                )
            )
        (self.root / "transcript.txt").write_text("Invented test passage.")
        (self.root / "boundaries.json").write_text("[]")
        self.image = self.root / "private-original-name.png"
        self.image.write_bytes(
            base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="
            )
        )
        self.payload = {
            "version": 1,
            "source": source,
            "scope_end": 95,
            "title": "Invented book",
            "author": "Test author",
            "works": [
                {
                    "reviewed": True,
                    "asset_source": str(self.image),
                    "private_note": "PRIVATE REVIEW",
                    "evidence": [{"manifest": str(self.manifest), "start": 20, "end": 30}],
                    "public": {
                        "id": "test-work",
                        "title": "A shape",
                        "collection": "exhibition",
                        "medium": "Drawing",
                        "description": "A synthetic shape.",
                        "attribution": "Unspecified",
                        "credit": "Test maker",
                        "note": "An interpretation.",
                        "alt": "A shape on paper.",
                    },
                }
            ],
        }
        self.output = self.root / "companion/visualizations/exhibition/exports/test"

    def test_export_has_only_public_fields_and_original_pixels(self):
        self.assertEqual(exhibition.export(self.payload, self.ctx, self.output), 1)
        catalog = json.loads((self.output / "catalog.json").read_text())
        text = json.dumps(catalog)
        for private in [
            str(self.root),
            "PRIVATE REVIEW",
            "scope_end",
            "manifest",
            "evidence",
            "private-original-name",
            "reviewed",
        ]:
            self.assertNotIn(private, text)
        self.assertEqual(set(p.name for p in self.output.iterdir()), {"catalog.json", "assets"})
        self.assertEqual((self.output / catalog["works"][0]["image"]).read_bytes(), self.image.read_bytes())

    def test_changed_source_and_rewound_progress_fail(self):
        changed = copy.deepcopy(self.payload)
        changed["source"]["mtime_ns"] += 1
        with self.assertRaisesRegex(ValueError, "source"):
            exhibition.prepare(changed, self.ctx)
        with self.assertRaisesRegex(ValueError, "listening limit"):
            exhibition.prepare(self.payload, (*self.ctx[:3], 80))

    def test_later_consulted_evidence_is_rejected_even_for_an_early_claim(self):
        self.payload["scope_end"] = 40
        with self.assertRaisesRegex(ValueError, "beyond selection scope"):
            exhibition.export(self.payload, self.ctx, self.output)
        self.assertFalse(self.output.exists())

    def test_missing_middle_chunk_rejected(self):
        (self.root / "chunk_001.json").unlink()
        with self.assertRaisesRegex(ValueError, "incomplete"):
            exhibition.prepare(self.payload, self.ctx)

    def test_claim_must_fit_source_and_reconstruction_needs_evidence(self):
        self.payload["works"][0]["evidence"][0]["end"] = 91
        with self.assertRaisesRegex(ValueError, "outside"):
            exhibition.prepare(self.payload, self.ctx)
        self.payload["works"][0]["evidence"] = []
        with self.assertRaisesRegex(ValueError, "passage evidence"):
            exhibition.prepare(self.payload, self.ctx)
        self.payload["works"][0]["public"]["collection"] = "interpretation"
        self.assertEqual(len(exhibition.prepare(self.payload, self.ctx)[0]["works"]), 1)

    def test_public_unknown_fields_and_unreviewed_content_refused(self):
        for field in ["prompt", "question", "answer", "listening_time", "image", "source_path"]:
            payload = copy.deepcopy(self.payload)
            payload["works"][0]["public"][field] = "Private content"
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "fields"):
                exhibition.prepare(payload, self.ctx)
        self.payload["works"][0]["reviewed"] = False
        with self.assertRaisesRegex(ValueError, "review"):
            exhibition.prepare(self.payload, self.ctx)

    def test_duplicate_ids_and_path_ids_refused(self):
        self.payload["works"].append(copy.deepcopy(self.payload["works"][0]))
        with self.assertRaisesRegex(ValueError, "unique"):
            exhibition.prepare(self.payload, self.ctx)
        self.payload["works"].pop()
        self.payload["works"][0]["public"]["id"] = "../escape"
        with self.assertRaisesRegex(ValueError, "slugs"):
            exhibition.prepare(self.payload, self.ctx)

    def test_placement_requires_evidence_and_rejects_private_fields(self):
        row = self.payload["works"][0]
        row["public"]["placement"] = {"room": "first-room", "label": "First room", "note": "Curated placement."}
        catalog, _ = exhibition.prepare(self.payload, self.ctx)
        self.assertEqual(catalog["works"][0]["placement"]["room"], "first-room")
        row["public"]["placement"]["manifest"] = "private-path"
        with self.assertRaisesRegex(ValueError, "fields"):
            exhibition.prepare(self.payload, self.ctx)
        del row["public"]["placement"]["manifest"]
        row["public"]["collection"] = "interpretation"
        row["evidence"] = []
        with self.assertRaisesRegex(ValueError, "Placement needs"):
            exhibition.prepare(self.payload, self.ctx)

    def test_embedded_metadata_and_trailing_bytes_refused(self):
        original = self.image.read_bytes()
        data = b"prompt\x00private generation words"
        chunk = struct.pack(">I", len(data)) + b"tEXt" + data + struct.pack(">I", zlib.crc32(b"tEXt" + data))
        self.image.write_bytes(original[:-12] + chunk + original[-12:])
        with self.assertRaisesRegex(ValueError, "metadata"):
            exhibition.prepare(self.payload, self.ctx)
        self.image.write_bytes(original + b"PRIVATE")
        with self.assertRaisesRegex(ValueError, "Unexpected data"):
            exhibition.prepare(self.payload, self.ctx)

    def test_object_reference_keeps_model_and_uses_asset_privacy_checks(self):
        row = self.payload["works"][0]
        row["public"]["object"] = "syrup-glass"
        row["reference_asset_source"] = row.pop("asset_source")
        catalog, assets = exhibition.prepare(self.payload, self.ctx)
        work = catalog["works"][0]
        self.assertEqual(work["object"], "syrup-glass")
        self.assertNotIn("image", work)
        self.assertEqual(assets[work["referenceImage"]], self.image.read_bytes())
        row["asset_source"] = str(self.image)
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            exhibition.prepare(self.payload, self.ctx)
        del row["asset_source"]
        self.image.write_bytes(self.image.read_bytes() + b"PRIVATE")
        with self.assertRaisesRegex(ValueError, "Unexpected data"):
            exhibition.prepare(self.payload, self.ctx)

    def test_frame_choices_and_reference_only_on_objects(self):
        row = self.payload["works"][0]
        for frame in exhibition.FRAMES:
            row["public"]["frame"] = frame
            self.assertEqual(exhibition.prepare(self.payload, self.ctx)[0]["works"][0]["frame"], frame)
        row["public"]["frame"] = "private path"
        with self.assertRaisesRegex(ValueError, "frame"):
            exhibition.prepare(self.payload, self.ctx)
        del row["public"]["frame"]
        row["reference_asset_source"] = str(self.image)
        with self.assertRaisesRegex(ValueError, "image work"):
            exhibition.prepare(self.payload, self.ctx)

    def test_ordered_montage_preserves_panels_and_rejects_private_fields(self):
        row = self.payload["works"][0]
        path = row.pop("asset_source")
        row["panel_assets"] = [
            {"title": "First", "alt": "First shape", "asset_source": path},
            {"title": "Second", "alt": "Second shape", "asset_source": path},
        ]
        catalog, assets = exhibition.prepare(self.payload, self.ctx)
        work = catalog["works"][0]
        self.assertEqual([p["title"] for p in work["panels"]], ["First", "Second"])
        self.assertEqual(work["image"], work["panels"][0]["image"])
        self.assertEqual(len(assets), 2)
        self.assertNotIn(path, json.dumps(catalog))
        row["panel_assets"][1]["prompt"] = "Private"
        with self.assertRaisesRegex(ValueError, "fields"):
            exhibition.prepare(self.payload, self.ctx)
        del row["panel_assets"][1]["prompt"]
        row["asset_source"] = path
        with self.assertRaisesRegex(ValueError, "another visual asset"):
            exhibition.prepare(self.payload, self.ctx)
        del row["asset_source"]
        row["panel_assets"].pop()
        with self.assertRaisesRegex(ValueError, "2 and 24"):
            exhibition.prepare(self.payload, self.ctx)

    def test_wall_text_requires_unframed_reference_and_rejects_ambiguous_displays(self):
        row = self.payload["works"][0]
        row["public"].update(wallText="Look closely.", frame="none")
        catalog, assets = exhibition.prepare(self.payload, self.ctx)
        work = catalog["works"][0]
        self.assertEqual(work["wallText"], "Look closely.")
        self.assertEqual(assets[work["image"]], self.image.read_bytes())
        for value in ("", " ", 12, "x" * 201):
            row["public"]["wallText"] = value
            with self.assertRaisesRegex(ValueError, "Wall text"):
                exhibition.prepare(self.payload, self.ctx)
        row["public"]["wallText"] = "Look closely."
        row["public"]["frame"] = "gallery"
        with self.assertRaisesRegex(ValueError, "Wall text"):
            exhibition.prepare(self.payload, self.ctx)
        row["public"]["frame"] = "none"
        row["public"]["object"] = "syrup-glass"
        with self.assertRaisesRegex(ValueError, "Wall text"):
            exhibition.prepare(self.payload, self.ctx)
        del row["public"]["object"]
        row["panel_assets"] = []
        with self.assertRaisesRegex(ValueError, "Wall text"):
            exhibition.prepare(self.payload, self.ctx)
        del row["panel_assets"]
        del row["asset_source"]
        with self.assertRaisesRegex(ValueError, "asset source"):
            exhibition.prepare(self.payload, self.ctx)

    def test_object_studies_keep_references_separate_and_reject_unknown_models(self):
        row = self.payload["works"][0]
        row["reference_asset_source"] = row.pop("asset_source")
        for model in exhibition.OBJECTS:
            row["public"]["object"] = model
            catalog, assets = exhibition.prepare(self.payload, self.ctx)
            work = catalog["works"][0]
            self.assertNotIn("image", work)
            self.assertEqual(assets[work["referenceImage"]], self.image.read_bytes())
        for bad in ("unsupported", [], None):
            row["public"]["object"] = bad
            with self.assertRaisesRegex(ValueError, "Unsupported object"):
                exhibition.prepare(self.payload, self.ctx)

    def test_alternate_images_remain_one_work_without_claiming_a_sequence(self):
        row = self.payload["works"][0]
        path = row.pop("asset_source")
        row["panel_assets"] = [
            {"title": value, "alt": value, "asset_source": path} for value in ("First version", "Second version")
        ]
        row["public"]["presentation"] = "variants"
        catalog, _ = exhibition.prepare(self.payload, self.ctx)
        self.assertEqual(len(catalog["works"]), 1)
        self.assertEqual(catalog["works"][0]["presentation"], "variants")
        for bad in ("private", [], None):
            row["public"]["presentation"] = bad
            with self.assertRaisesRegex(ValueError, "Presentation"):
                exhibition.prepare(self.payload, self.ctx)
        row["public"]["presentation"] = "variants"
        del row["panel_assets"]
        with self.assertRaisesRegex(ValueError, "Presentation"):
            exhibition.prepare(self.payload, self.ctx)

    def test_outputs_are_private_and_immutable(self):
        with self.assertRaisesRegex(ValueError, "ignored"):
            exhibition.export(self.payload, self.ctx, self.root / "public")
        exhibition.export(self.payload, self.ctx, self.output)
        before = (self.output / "catalog.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "already exists"):
            exhibition.export(self.payload, self.ctx, self.output)
        self.assertEqual((self.output / "catalog.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
