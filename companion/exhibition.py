"""Prepare a curated public collection from an explicitly reviewed private selection.

This is an export allowlist, not an automatic detector of spoilers or private prose.
The exporter never searches journals, prompts, or artwork directories.
"""

import argparse
import hashlib
import json
import re
import shutil
import struct
import tempfile
from pathlib import Path

from journal import context, interval, number, write_json
from position import ROOT
from transcript_io import validate_run

PUBLIC_FIELDS = {
    "id",
    "title",
    "collection",
    "medium",
    "description",
    "attribution",
    "credit",
    "note",
    "alt",
    "object",
    "placement",
}
REQUIRED_FIELDS = PUBLIC_FIELDS - {"object", "placement"}


def exact_keys(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= value.keys() or set(value) - set(required) - set(optional):
        raise ValueError("Missing or unrecognized fields; do not pass private records through to public output")


def private_path(path):
    resolved = Path(path).resolve()
    private = (ROOT / "companion/visualizations").resolve()
    if resolved == private or private not in resolved.parents:
        raise ValueError("Selection and output must live under the ignored companion/visualizations directory")
    return resolved


def png_bytes(path):
    """Accept PNG artwork only; reject embedded prose/EXIF rather than exporting it."""
    data = path.read_bytes()
    if path.suffix.lower() != ".png" or not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Artwork must be a PNG file")
    cursor = 8
    while cursor + 12 <= len(data):
        length = struct.unpack(">I", data[cursor : cursor + 4])[0]
        kind = data[cursor + 4 : cursor + 8]
        if kind in {b"tEXt", b"iTXt", b"zTXt", b"eXIf"}:
            raise ValueError("Artwork contains embedded metadata; review and sanitize it before export")
        cursor += length + 12
        if cursor > len(data):
            raise ValueError("Truncated PNG artwork")
        if kind == b"IEND":
            if cursor != len(data):
                raise ValueError("Unexpected data after PNG artwork")
            return data
    raise ValueError("Incomplete PNG artwork")


def prepare(payload, ctx):
    """Validate source and all evidence before preparing the explicitly public fields."""
    _, source, _, safe_end = ctx
    exact_keys(payload, {"version", "source", "scope_end", "title", "author", "works"})
    if payload["version"] != 1 or isinstance(payload["version"], bool):
        raise ValueError("Unsupported selection version")
    if payload["source"] != source:
        raise ValueError("Selection belongs to a different or changed source")
    limit = number(payload["scope_end"])
    if limit > safe_end:
        raise ValueError("Selection exceeds the buffered listening limit")
    for key in ("title", "author"):
        if not isinstance(payload[key], str) or not payload[key].strip():
            raise ValueError("Collection title and author must be nonempty text")
    if not isinstance(payload["works"], list) or not payload["works"]:
        raise ValueError("Select at least one work explicitly")
    seen, works, assets, checked = set(), [], {}, {}
    for row in payload["works"]:
        exact_keys(row, {"public", "reviewed", "evidence"}, {"asset_source", "private_note"})
        if row["reviewed"] is not True:
            raise ValueError("Each selected work needs an explicit public-content review")
        work = row["public"]
        exact_keys(work, REQUIRED_FIELDS, {"object", "placement"})
        if any(not isinstance(work[k], str) or not work[k].strip() for k in REQUIRED_FIELDS):
            raise ValueError("Public work fields must be nonempty text")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", work["id"]) or work["id"] in seen:
            raise ValueError("Work IDs must be unique, stable lowercase slugs")
        seen.add(work["id"])
        if work["collection"] not in {"exhibition", "interpretation"}:
            raise ValueError("Unknown work collection")
        if not isinstance(row["evidence"], list):
            raise ValueError("Evidence must be a list")
        if work["collection"] == "exhibition" and not row["evidence"]:
            raise ValueError("Exhibition reconstructions need passage evidence")
        if "placement" in work:
            placement = work["placement"]
            exact_keys(placement, {"room", "label", "note"})
            if any(not isinstance(value, str) or not value.strip() for value in placement.values()):
                raise ValueError("Placement fields must be nonempty text")
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", placement["room"]):
                raise ValueError("Placement room must be a stable slug")
            if not row["evidence"]:
                raise ValueError("Placement needs passage evidence")
        for evidence in row["evidence"]:
            exact_keys(evidence, {"manifest", "start", "end"})
            span = interval({"start": evidence["start"], "end": evidence["end"]})
            path = (ROOT / evidence["manifest"]).resolve()
            if path not in checked:
                manifest = json.loads(path.read_text())
                if (
                    (ROOT / manifest["source_audio"]).resolve() != Path(source["path"])
                    or manifest["source_size"] != source["size"]
                    or manifest["source_mtime_ns"] != source["mtime_ns"]
                ):
                    raise ValueError("Evidence belongs to a different or changed source")
                envelope = interval({"start": manifest["section_start"], "end": manifest["section_end"]})
                if envelope["end"] > limit:
                    raise ValueError("Consulted transcript extends beyond selection scope")
                validate_run(path.parent, manifest)
                checked[path] = envelope
            envelope = checked[path]
            if not envelope["start"] <= span["start"] < span["end"] <= envelope["end"]:
                raise ValueError("Claim interval is outside its evidence")
        public = dict(work)
        if "object" in work:
            if work["object"] != "syrup-glass" or "asset_source" in row:
                raise ValueError("Unsupported object or ambiguous asset source")
        else:
            if not isinstance(row.get("asset_source"), str):
                raise ValueError("An image work needs an explicit asset source")
            path = (ROOT / row["asset_source"]).resolve()
            data = png_bytes(path)
            digest = hashlib.sha256(data).hexdigest()[:16]
            name = f"assets/{work['id']}-{digest}.png"
            assets[name] = data
            public["image"] = name
        works.append(public)
    return {"version": 1, "title": payload["title"], "author": payload["author"], "works": works}, assets


def export(payload, ctx, output):
    output = private_path(output)
    if output.exists():
        raise ValueError("Output already exists; use a fresh directory to preserve prior exports")
    catalog, assets = prepare(payload, ctx)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".pending-", dir=output.parent))
    try:
        (staging / "assets").mkdir()
        for name, data in assets.items():
            (staging / name).write_bytes(data)
        write_json(staging / "catalog.json", catalog)
        staging.rename(output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return len(catalog["works"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check", "export"])
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        selection = private_path(args.input)
        ctx = context()
        payload = json.loads(selection.read_text())
        if args.command == "check":
            catalog, _ = prepare(payload, ctx)
            print(f"Selection valid: {len(catalog['works'])} reviewed works; no files exported")
        else:
            if args.output is None:
                parser.error("export requires --output")
            count = export(payload, ctx, args.output)
            print(f"Prepared {count} works in {args.output}. Review before copying to a public repository.")
    except (ValueError, KeyError, TypeError, OSError) as error:
        raise SystemExit(f"Export refused: {error}") from error


if __name__ == "__main__":
    main()
